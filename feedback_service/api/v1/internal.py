"""api/v1/internal.py — Internal service-to-service endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from core.dependencies import DbDep, InternalDep
from models.feedback import Feedback, FeedbackType

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get(
    "/feedback/by-post/{post_id}",
    summary="Aggregate feedback for a CMS post (internal)",
    dependencies=[InternalDep],
)
async def feedback_by_post(
    post_id: uuid.UUID,
    db:      DbDep,
    limit:   int           = Query(default=20, ge=1, le=100),
    skip:    int           = Query(default=0,  ge=0),
    detail:  Optional[str] = Query(default=None),
) -> dict:
    rows = (await db.execute(
        select(Feedback.feedback_type, func.count(Feedback.id).label("cnt"))
        .where(Feedback.post_id == post_id)
        .group_by(Feedback.feedback_type)
    )).all()

    by_type: dict[str, int] = {t.value: 0 for t in FeedbackType}
    total = 0
    for row in rows:
        key = row.feedback_type.value if hasattr(row.feedback_type, "value") else str(row.feedback_type)
        by_type[key] = row.cnt
        total += row.cnt

    recent: list[dict] = []
    if detail == "true":
        items = (await db.execute(
            select(
                Feedback.id, Feedback.unique_ref, Feedback.feedback_type,
                Feedback.subject, Feedback.status, Feedback.submitted_at,
                Feedback.is_anonymous, Feedback.submitter_name,
            )
            .where(Feedback.post_id == post_id)
            .order_by(Feedback.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )).all()

        for item in items:
            recent.append({
                "id":            str(item.id),
                "unique_ref":    item.unique_ref,
                "feedback_type": item.feedback_type.value if hasattr(item.feedback_type, "value") else str(item.feedback_type),
                "subject":       item.subject,
                "status":        item.status.value if hasattr(item.status, "value") else str(item.status),
                "submitted_at":  item.submitted_at.isoformat() if item.submitted_at else None,
                "submitter":     None if item.is_anonymous else item.submitter_name,
            })

    return {
        "post_id": str(post_id),
        "total":   total,
        "by_type": by_type,
        "recent":  recent,
    }
