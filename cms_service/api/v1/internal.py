"""api/v1/internal.py — Service-to-service internal CMS endpoints.

Secured by X-Service-Key header (INTERNAL_SERVICE_KEY from settings).
No JWT auth — these endpoints are called by other Riviwa services only.

Endpoints
─────────
  GET  /api/v1/internal/cms/{org_id}/posts   List published posts for an org
  POST /api/v1/internal/cms/{org_id}/faq     Create a FAQ post in DRAFT status
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from core.dependencies import DbDep, InternalDep
from models.post import OrgPost, PostStatus, PostType

router = APIRouter(prefix="/internal/cms", tags=["Internal — CMS"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return re.sub(r"^-+|-+$", "", s)


# ── Schemas (internal-only, not worth a separate schemas file) ─────────────────

class FaqCreateBody(BaseModel):
    title:           str
    content:         str
    created_by_note: Optional[str] = None


# ── GET /internal/cms/{org_id}/posts ──────────────────────────────────────────

@router.get(
    "/{org_id}/posts",
    summary="[Internal] List published posts for an org",
)
async def internal_list_org_posts(
    org_id:    uuid.UUID,
    db:        DbDep,
    _:         InternalDep,
    post_type: Optional[PostType] = Query(default=None,
                                          description="Filter by post type, e.g. ANNOUNCEMENT, BLOG"),
    skip:      int                = Query(default=0,   ge=0),
    limit:     int                = Query(default=50,  ge=1, le=200),
) -> list[dict]:
    """Return published posts (optionally filtered by post_type) for the given org.

    Used by AI and other services to fetch FAQs / announcements / articles
    without requiring a user JWT.
    """
    q = select(OrgPost).where(
        OrgPost.org_id == org_id,
        OrgPost.status == PostStatus.PUBLISHED,
        OrgPost.deleted_at.is_(None),
    )
    if post_type:
        q = q.where(OrgPost.post_type == post_type)

    rows = (await db.execute(
        q.order_by(OrgPost.is_pinned.desc(), OrgPost.published_at.desc())
         .offset(skip).limit(limit)
    )).scalars().all()

    return [
        {
            "id":           str(post.id),
            "title":        post.title,
            "slug":         post.slug,
            "post_type":    post.post_type.value,
            "excerpt":      post.excerpt,
            "content":      post.content,
            "published_at": post.published_at.isoformat() if post.published_at else None,
        }
        for post in rows
    ]


# ── POST /internal/cms/{org_id}/faq ───────────────────────────────────────────

@router.post(
    "/{org_id}/faq",
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Create a FAQ post in DRAFT status",
)
async def internal_create_faq(
    org_id: uuid.UUID,
    body:   FaqCreateBody,
    db:     DbDep,
    _:      InternalDep,
) -> dict:
    """Create a DRAFT FAQ post on behalf of an AI service or other internal caller.

    Uses PostType.BLOG (the closest generic content type) since there is no
    dedicated FAQ type in the PostType enum. The post is created in DRAFT status
    and must be reviewed/published by org staff via the normal CMS workflow.

    `created_by_note` is stored in author_name for audit visibility.
    """
    slug = _slugify(body.title)

    # Ensure slug uniqueness within the org; append a short UUID suffix on collision
    existing = (await db.execute(
        select(OrgPost).where(
            OrgPost.org_id == org_id,
            OrgPost.slug == slug,
            OrgPost.deleted_at.is_(None),
        )
    )).scalars().first()
    if existing:
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    post = OrgPost(
        org_id=org_id,
        title=body.title,
        slug=slug,
        content=body.content,
        post_type=PostType.BLOG,          # FAQ posts use BLOG (no dedicated FAQ type)
        status=PostStatus.DRAFT,
        author_name=body.created_by_note or "AI Assistant",
        is_public=True,
        allows_feedback=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {
        "post_id": str(post.id),
        "title":   post.title,
        "status":  post.status.value,
    }
