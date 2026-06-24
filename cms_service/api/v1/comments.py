"""api/v1/comments.py — Post comments with moderation."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query, status
from sqlalchemy import select

from core.dependencies import AuthDep, DbDep, StaffDep
from core.exceptions import ForbiddenError, NotFoundError
from models.post import CommentStatus, OrgPost, OrgPostComment, PostStatus
from schemas.post import CommentCreate, CommentModerate, CommentOut

router = APIRouter(prefix="/cms", tags=["CMS — Comments"])


async def _get_comment_or_404(comment_id: uuid.UUID, db: DbDep) -> OrgPostComment:
    c = (await db.execute(
        select(OrgPostComment).where(
            OrgPostComment.id == comment_id,
            OrgPostComment.deleted_at.is_(None),
        )
    )).scalars().first()
    if not c:
        raise NotFoundError("Comment not found.")
    return c


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut],
            summary="List approved comments for a post")
async def list_comments(
    post_id:   uuid.UUID,
    db:        DbDep,
    claims:    AuthDep,
    include_pending: bool = Query(default=False),
) -> list[CommentOut]:
    q = select(OrgPostComment).where(
        OrgPostComment.post_id == post_id,
        OrgPostComment.parent_id.is_(None),
        OrgPostComment.deleted_at.is_(None),
    )
    is_staff = claims.org_role in ("owner", "admin", "manager") or \
               claims.platform_role in ("super_admin", "admin")
    if not (is_staff and include_pending):
        q = q.where(OrgPostComment.status == CommentStatus.APPROVED)
    q = q.order_by(OrgPostComment.created_at)

    top_level = (await db.execute(q)).scalars().all()
    result = []
    for comment in top_level:
        replies = (await db.execute(
            select(OrgPostComment).where(
                OrgPostComment.parent_id == comment.id,
                OrgPostComment.status == CommentStatus.APPROVED,
                OrgPostComment.deleted_at.is_(None),
            ).order_by(OrgPostComment.created_at)
        )).scalars().all()
        out = CommentOut.model_validate(comment)
        out.replies = [CommentOut.model_validate(r) for r in replies]
        result.append(out)
    return result


@router.post("/posts/{post_id}/comments", response_model=CommentOut,
             status_code=status.HTTP_201_CREATED, summary="Add comment to post")
async def add_comment(post_id: uuid.UUID, body: CommentCreate,
                      db: DbDep, claims: AuthDep) -> CommentOut:
    post = (await db.execute(
        select(OrgPost).where(OrgPost.id == post_id, OrgPost.deleted_at.is_(None))
    )).scalars().first()
    if not post:
        raise NotFoundError("Post not found.")
    if not post.allows_comments:
        raise ForbiddenError(message="Comments are disabled for this post.")
    if post.status != PostStatus.PUBLISHED:
        raise ForbiddenError(message="Cannot comment on unpublished posts.")

    is_staff = claims.org_role in ("owner", "admin", "manager", "editor")
    comment = OrgPostComment(
        post_id=post_id,
        parent_id=body.parent_id,
        user_id=claims.user_id,
        author_name=body.author_name,
        author_email=body.author_email,
        content=body.content,
        status=CommentStatus.APPROVED if is_staff else CommentStatus.PENDING,
        is_staff_reply=is_staff,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    out = CommentOut.model_validate(comment)
    out.replies = []
    return out


@router.put("/comments/{comment_id}/moderate", response_model=CommentOut,
            summary="Approve or reject a comment")
async def moderate_comment(comment_id: uuid.UUID, body: CommentModerate,
                           db: DbDep, claims: StaffDep) -> CommentOut:
    comment = await _get_comment_or_404(comment_id, db)
    comment.status = body.status
    comment.moderated_by_id = claims.user_id
    comment.moderation_note = body.moderation_note
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    out = CommentOut.model_validate(comment)
    out.replies = []
    return out


@router.delete("/comments/{comment_id}", status_code=status.HTTP_200_OK,
               summary="Soft-delete a comment")
async def delete_comment(comment_id: uuid.UUID, db: DbDep, claims: StaffDep) -> dict:
    comment = await _get_comment_or_404(comment_id, db)
    from datetime import datetime, timezone
    comment.deleted_at = datetime.now(timezone.utc)
    db.add(comment)
    await db.commit()
    return {"deleted": True, "comment_id": str(comment_id)}
