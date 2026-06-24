"""api/v1/posts.py — CMS post CRUD and publish workflow."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlmodel import col

from core.dependencies import AuthDep, DbDep, StaffDep
from core.exceptions import ConflictError, ForbiddenError, NotFoundError
from events.producer import publish_cms_event
from events.topics import CmsEvents
from models.post import (
    OrgPost, OrgPostCategory, OrgPostCategoryLink,
    OrgPostRevision, PostStatus, PostType,
)
from schemas.post import (
    PostCreate, PostListOut, PostOut, PostSchedule, PostUpdate, RevisionOut,
)

router = APIRouter(prefix="/cms/posts", tags=["CMS — Posts"])


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return re.sub(r"^-+|-+$", "", s)


async def _get_post_or_404(post_id: uuid.UUID, db: DbDep) -> OrgPost:
    post = (await db.execute(
        select(OrgPost).where(
            OrgPost.id == post_id,
            OrgPost.deleted_at.is_(None),
        )
    )).scalars().first()
    if not post:
        raise NotFoundError("Post not found.")
    return post


async def _get_post_categories(post_id: uuid.UUID, db: DbDep) -> list[dict]:
    rows = (await db.execute(
        select(OrgPostCategory)
        .join(OrgPostCategoryLink, OrgPostCategoryLink.category_id == OrgPostCategory.id)
        .where(OrgPostCategoryLink.post_id == post_id)
        .order_by(OrgPostCategory.sort_order)
    )).scalars().all()
    return [{"id": str(c.id), "name": c.name, "slug": c.slug} for c in rows]


async def _set_post_categories(post_id: uuid.UUID, category_ids: list[uuid.UUID], db: DbDep) -> None:
    await db.execute(
        OrgPostCategoryLink.__table__.delete().where(
            OrgPostCategoryLink.post_id == post_id
        )
    )
    for cid in category_ids:
        db.add(OrgPostCategoryLink(post_id=post_id, category_id=cid))


def _post_to_out(post: OrgPost, categories: list[dict]) -> PostOut:
    return PostOut(
        id=post.id, org_id=post.org_id, branch_id=post.branch_id,
        title=post.title, slug=post.slug, excerpt=post.excerpt,
        content=post.content, post_type=post.post_type.value,
        status=post.status.value, tags=post.tags or [],
        featured_image_url=post.featured_image_url,
        featured_image_alt=post.featured_image_alt,
        seo_title=post.seo_title, seo_description=post.seo_description,
        author_id=post.author_id, author_name=post.author_name,
        editor_id=post.editor_id, editor_name=post.editor_name,
        scheduled_at=post.scheduled_at, published_at=post.published_at,
        view_count=post.view_count, is_pinned=post.is_pinned,
        is_featured=post.is_featured, allows_comments=post.allows_comments,
        is_public=post.is_public, target_audience=post.target_audience,
        created_at=post.created_at, updated_at=post.updated_at,
        categories=categories,
    )


# ── List posts ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PostListOut, summary="List CMS posts")
async def list_posts(
    db:          DbDep,
    claims:      AuthDep,
    org_id:      Optional[uuid.UUID] = Query(default=None),
    post_type:   Optional[PostType]  = Query(default=None),
    status_:     Optional[PostStatus] = Query(default=None, alias="status"),
    tag:         Optional[str]       = Query(default=None),
    is_featured: Optional[bool]      = Query(default=None),
    is_pinned:   Optional[bool]      = Query(default=None),
    skip:        int                 = Query(default=0,  ge=0),
    limit:       int                 = Query(default=20, ge=1, le=100),
) -> PostListOut:
    q = select(OrgPost).where(OrgPost.deleted_at.is_(None))

    # Scope: non-admins see only their org; admins can filter
    is_admin = claims.platform_role in ("super_admin", "admin")
    if not is_admin:
        if not claims.org_id:
            return PostListOut(items=[], count=0, total=0, skip=skip, limit=limit)
        q = q.where(OrgPost.org_id == claims.org_id)
    elif org_id:
        q = q.where(OrgPost.org_id == org_id)

    if post_type:
        q = q.where(OrgPost.post_type == post_type)
    if status_:
        q = q.where(OrgPost.status == status_)
    else:
        # Default: staff sees DRAFT+IN_REVIEW+PUBLISHED; public sees PUBLISHED
        is_staff = claims.org_role in ("owner", "admin", "manager", "editor") or is_admin
        if not is_staff:
            q = q.where(OrgPost.status == PostStatus.PUBLISHED, OrgPost.is_public == True)
    if tag:
        q = q.where(OrgPost.tags.contains([tag]))
    if is_featured is not None:
        q = q.where(OrgPost.is_featured == is_featured)
    if is_pinned is not None:
        q = q.where(OrgPost.is_pinned == is_pinned)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(
        q.order_by(OrgPost.is_pinned.desc(), OrgPost.published_at.desc(), OrgPost.created_at.desc())
         .offset(skip).limit(limit)
    )).scalars().all()

    items = []
    for post in rows:
        cats = await _get_post_categories(post.id, db)
        items.append(_post_to_out(post, cats))
    return PostListOut(items=items, count=len(items), total=total, skip=skip, limit=limit)


# ── Create post ────────────────────────────────────────────────────────────────

@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED,
             summary="Create a new post (draft)")
async def create_post(body: PostCreate, db: DbDep, claims: StaffDep) -> PostOut:
    org_id = body.branch_id and claims.org_id or claims.org_id
    if not claims.org_id:
        raise ForbiddenError(message="Organisation membership required.")

    slug = body.slug or _slugify(body.title)
    existing = (await db.execute(
        select(OrgPost).where(
            OrgPost.org_id == claims.org_id,
            OrgPost.slug == slug,
            OrgPost.deleted_at.is_(None),
        )
    )).scalars().first()
    if existing:
        raise ConflictError(f"A post with slug '{slug}' already exists in this organisation.")

    post = OrgPost(
        org_id=claims.org_id,
        branch_id=body.branch_id,
        title=body.title,
        slug=slug,
        excerpt=body.excerpt,
        content=body.content,
        post_type=body.post_type,
        status=PostStatus.DRAFT,
        tags=body.tags,
        featured_image_url=body.featured_image_url,
        featured_image_alt=body.featured_image_alt,
        seo_title=body.seo_title,
        seo_description=body.seo_description,
        author_id=claims.user_id,
        author_name=None,
        is_public=body.is_public,
        target_audience=body.target_audience,
        allows_comments=body.allows_comments,
        is_pinned=body.is_pinned,
        is_featured=body.is_featured,
    )
    db.add(post)
    await db.flush()

    if body.category_ids:
        await _set_post_categories(post.id, body.category_ids, db)

    db.add(OrgPostRevision(
        post_id=post.id, title=post.title, content=post.content,
        excerpt=post.excerpt, revised_by_id=claims.user_id, revision_number=1,
        revision_note="Initial draft",
    ))
    await db.commit()
    await db.refresh(post)
    cats = await _get_post_categories(post.id, db)
    return _post_to_out(post, cats)


# ── Get post ───────────────────────────────────────────────────────────────────

@router.get("/{post_id}", response_model=PostOut, summary="Get post by ID")
async def get_post(post_id: uuid.UUID, db: DbDep, claims: AuthDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)
    cats = await _get_post_categories(post_id, db)

    # Track view for published posts
    if post.status == PostStatus.PUBLISHED:
        await db.execute(
            update(OrgPost).where(OrgPost.id == post_id)
            .values(view_count=OrgPost.view_count + 1)
        )
        await db.commit()

    return _post_to_out(post, cats)


# ── Update post ────────────────────────────────────────────────────────────────

@router.put("/{post_id}", response_model=PostOut, summary="Update post content")
async def update_post(post_id: uuid.UUID, body: PostUpdate, db: DbDep, claims: StaffDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)

    rev_number = (await db.execute(
        select(func.count(OrgPostRevision.id)).where(OrgPostRevision.post_id == post_id)
    )).scalar_one() + 1

    for field, value in body.model_dump(exclude_none=True, exclude={"category_ids", "revision_note"}).items():
        if hasattr(post, field):
            setattr(post, field, value)

    if body.slug:
        existing = (await db.execute(
            select(OrgPost).where(
                OrgPost.org_id == post.org_id, OrgPost.slug == body.slug,
                OrgPost.id != post_id, OrgPost.deleted_at.is_(None),
            )
        )).scalars().first()
        if existing:
            raise ConflictError(f"Slug '{body.slug}' is already taken.")

    if body.category_ids is not None:
        await _set_post_categories(post_id, body.category_ids, db)

    db.add(OrgPostRevision(
        post_id=post_id, title=post.title, content=post.content,
        excerpt=post.excerpt, revised_by_id=claims.user_id,
        revised_by_name=None, revision_note=body.revision_note,
        revision_number=rev_number,
    ))
    db.add(post)
    await db.commit()
    await db.refresh(post)
    cats = await _get_post_categories(post_id, db)
    return _post_to_out(post, cats)


# ── Publish / workflow transitions ─────────────────────────────────────────────

@router.post("/{post_id}/publish", response_model=PostOut, summary="Publish post")
async def publish_post(post_id: uuid.UUID, db: DbDep, claims: StaffDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)
    if post.status == PostStatus.PUBLISHED:
        raise ConflictError("Post is already published.")
    post.status       = PostStatus.PUBLISHED
    post.published_at = datetime.now(timezone.utc)
    post.editor_id    = claims.user_id
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await publish_cms_event(CmsEvents.POST_PUBLISHED, {
        "post_id": str(post.id), "org_id": str(post.org_id),
        "title": post.title, "post_type": post.post_type.value,
        "slug": post.slug, "is_public": post.is_public,
    }, key=str(post.org_id))
    cats = await _get_post_categories(post_id, db)
    return _post_to_out(post, cats)


@router.post("/{post_id}/schedule", response_model=PostOut, summary="Schedule post for future publish")
async def schedule_post(post_id: uuid.UUID, body: PostSchedule, db: DbDep, claims: StaffDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)
    if body.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="scheduled_at must be in the future.")
    post.status       = PostStatus.SCHEDULED
    post.scheduled_at = body.scheduled_at
    post.editor_id    = claims.user_id
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await publish_cms_event(CmsEvents.POST_SCHEDULED, {
        "post_id": str(post.id), "org_id": str(post.org_id),
        "scheduled_at": body.scheduled_at.isoformat(),
    }, key=str(post.org_id))
    cats = await _get_post_categories(post_id, db)
    return _post_to_out(post, cats)


@router.post("/{post_id}/submit-review", response_model=PostOut, summary="Submit post for review")
async def submit_for_review(post_id: uuid.UUID, db: DbDep, claims: StaffDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)
    if post.status != PostStatus.DRAFT:
        raise ConflictError("Only DRAFT posts can be submitted for review.")
    post.status = PostStatus.IN_REVIEW
    db.add(post)
    await db.commit()
    await db.refresh(post)
    cats = await _get_post_categories(post_id, db)
    return _post_to_out(post, cats)


@router.post("/{post_id}/archive", response_model=PostOut, summary="Archive post")
async def archive_post(post_id: uuid.UUID, db: DbDep, claims: StaffDep) -> PostOut:
    post = await _get_post_or_404(post_id, db)
    post.status = PostStatus.ARCHIVED
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await publish_cms_event(CmsEvents.POST_ARCHIVED, {
        "post_id": str(post.id), "org_id": str(post.org_id),
    }, key=str(post.org_id))
    cats = await _get_post_categories(post_id, db)
    return _post_to_out(post, cats)


@router.delete("/{post_id}", status_code=status.HTTP_200_OK, summary="Soft-delete post")
async def delete_post(post_id: uuid.UUID, db: DbDep, claims: StaffDep) -> dict:
    post = await _get_post_or_404(post_id, db)
    post.deleted_at = datetime.now(timezone.utc)
    db.add(post)
    await db.commit()
    return {"deleted": True, "post_id": str(post_id)}


# ── Revisions ──────────────────────────────────────────────────────────────────

@router.get("/{post_id}/revisions", response_model=list[RevisionOut],
            summary="List all revisions for a post")
async def list_revisions(post_id: uuid.UUID, db: DbDep, claims: StaffDep) -> list[RevisionOut]:
    await _get_post_or_404(post_id, db)
    rows = (await db.execute(
        select(OrgPostRevision)
        .where(OrgPostRevision.post_id == post_id)
        .order_by(OrgPostRevision.revision_number.desc())
    )).scalars().all()
    return [RevisionOut.model_validate(r) for r in rows]


# ── Public feed ────────────────────────────────────────────────────────────────

@router.get("/public/{org_id}/feed", summary="Public published posts for an org (no auth)")
async def public_feed(
    org_id:    uuid.UUID,
    db:        DbDep,
    post_type: Optional[PostType] = Query(default=None),
    tag:       Optional[str]      = Query(default=None),
    skip:      int                = Query(default=0,  ge=0),
    limit:     int                = Query(default=20, ge=1, le=100),
) -> dict:
    q = select(OrgPost).where(
        OrgPost.org_id == org_id,
        OrgPost.status == PostStatus.PUBLISHED,
        OrgPost.is_public == True,
        OrgPost.deleted_at.is_(None),
    )
    if post_type:
        q = q.where(OrgPost.post_type == post_type)
    if tag:
        q = q.where(OrgPost.tags.contains([tag]))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(
        q.order_by(OrgPost.is_pinned.desc(), OrgPost.published_at.desc())
         .offset(skip).limit(limit)
    )).scalars().all()

    items = []
    for post in rows:
        cats = await _get_post_categories(post.id, db)
        items.append(_post_to_out(post, cats))
    return {"items": items, "count": len(items), "total": total, "skip": skip, "limit": limit}
