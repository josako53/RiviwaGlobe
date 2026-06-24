"""api/v1/post_feedback.py — Riviwa feedback integration for CMS posts.

Replaces the traditional comment system. Each post can receive feedback
(applause, suggestion, grievance, inquiry) via the Riviwa AI conversation.

Endpoints
─────────
  GET  /cms/posts/{post_id}/feedback/summary
       Returns aggregate counts by feedback type for a post.
       Calls feedback_service internal endpoint.

  POST /cms/posts/{post_id}/feedback/start
       Starts a Riviwa AI conversation scoped to this post.
       Calls ai_service and returns conversation_id + opening message.
       No auth required — Consumers submit anonymously or with a web_token.

  GET  /cms/posts/{post_id}/feedback
       Returns recent feedback items for the post (auth required — staff only).
"""
from __future__ import annotations

import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Query, status
from sqlalchemy import select

from core.config import settings
from core.dependencies import AuthDep, DbDep, OptTokenDep, StaffDep
from core.exceptions import ForbiddenError, NotFoundError
from models.post import OrgPost, PostStatus

router = APIRouter(tags=["CMS — Post Feedback"])

_FEEDBACK_BASE = settings.FEEDBACK_SERVICE_URL
_AI_BASE       = settings.AI_SERVICE_URL
_TIMEOUT       = 10.0


async def _get_published_post(post_id: uuid.UUID, db: DbDep) -> OrgPost:
    post = (await db.execute(
        select(OrgPost).where(
            OrgPost.id == post_id,
            OrgPost.deleted_at.is_(None),
        )
    )).scalars().first()
    if not post:
        raise NotFoundError("Post not found.")
    return post


# ── Summary (public — no auth) ────────────────────────────────────────────────

@router.get(
    "/cms/posts/{post_id}/feedback/summary",
    summary="Get feedback summary for a post",
    description=(
        "Returns aggregate feedback counts (applause / suggestion / grievance / inquiry) "
        "for this post. No authentication required."
    ),
)
async def get_post_feedback_summary(post_id: uuid.UUID, db: DbDep) -> dict:
    await _get_published_post(post_id, db)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_FEEDBACK_BASE}/internal/feedback/by-post/{post_id}",
            headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
        )

    if resp.status_code == 200:
        return resp.json()

    # Feedback service unavailable — return zero counts gracefully
    return {
        "post_id": str(post_id),
        "total": 0,
        "by_type": {"applause": 0, "suggestion": 0, "grievance": 0, "inquiry": 0},
        "recent": [],
    }


# ── Start feedback conversation (public — no auth required) ───────────────────

@router.post(
    "/cms/posts/{post_id}/feedback/start",
    status_code=status.HTTP_201_CREATED,
    summary="Start a feedback conversation for a post",
    description=(
        "Initiates a Riviwa AI conversation scoped to this CMS post. "
        "The AI will ask the Consumer what type of feedback they have "
        "(applause, suggestion, grievance, or inquiry) and capture all details. "
        "No authentication required."
    ),
)
async def start_post_feedback(
    post_id:    uuid.UUID,
    db:         DbDep,
    token:      OptTokenDep,
    language:   str           = Query(default="sw", description="sw | en"),
    web_token:  Optional[str] = Query(default=None, description="Anonymous session token"),
) -> dict:
    post = await _get_published_post(post_id, db)

    if not post.allows_feedback:
        raise ForbiddenError("Feedback is disabled for this post.")

    if post.status != PostStatus.PUBLISHED:
        raise ForbiddenError("Feedback can only be submitted on published posts.")

    user_id = str(token.user_id) if token else None

    payload = {
        "channel":     "web",
        "language":    language,
        "org_id":      str(post.org_id),
        "post_id":     str(post_id),
        "post_slug":   post.slug,
        "post_title":  post.title,
    }
    if user_id:
        payload["user_id"] = user_id
    if web_token:
        payload["web_token"] = web_token

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{_AI_BASE}/api/v1/ai/conversations",
            json=payload,
        )

    resp.raise_for_status()
    data = resp.json()

    return {
        "conversation_id": data.get("conversation_id"),
        "reply":           data.get("reply"),
        "post_id":         str(post_id),
        "post_title":      post.title,
        "post_slug":       post.slug,
        "org_id":          str(post.org_id),
        "language":        language,
    }


# ── Recent feedback items (staff only) ───────────────────────────────────────

@router.get(
    "/cms/posts/{post_id}/feedback",
    summary="List feedback submitted for a post (staff only)",
)
async def list_post_feedback(
    post_id: uuid.UUID,
    db:      DbDep,
    claims:  StaffDep,
    limit:   int = Query(default=20, ge=1, le=100),
    skip:    int = Query(default=0, ge=0),
) -> dict:
    await _get_published_post(post_id, db)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_FEEDBACK_BASE}/internal/feedback/by-post/{post_id}",
            headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
            params={"limit": limit, "skip": skip, "detail": "true"},
        )

    if resp.status_code == 200:
        return resp.json()

    return {
        "post_id": str(post_id),
        "total": 0,
        "by_type": {"applause": 0, "suggestion": 0, "grievance": 0, "inquiry": 0},
        "recent": [],
    }
