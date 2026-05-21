"""api/v1/recommendations.py — Recommendation and similarity endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from core.dependencies import CurrentUser, DbDep
from models.entity import ActivityEvent
from repositories.entity_repository import EntityRepository
from schemas.recommendation import RecommendationResponse, SimilarResponse
from services.recommendation_service import RecommendationOrchestrator

router = APIRouter(tags=["Recommendations"])

_FEEDBACK_SIGNALS = {"helpful", "not_helpful", "dismissed"}
_FEEDBACK_EVENT_TYPES = {
    "helpful":     "recommendation_helpful",
    "not_helpful": "recommendation_not_helpful",
    "dismissed":   "recommendation_dismissed",
}


class FeedbackRequest(BaseModel):
    signal: str  # helpful | not_helpful | dismissed


@router.get(
    "/recommendations/{entity_id}",
    response_model=RecommendationResponse,
    summary="Get recommendations for an entity",
    description=(
        "Returns entities recommended for the given entity based on semantic similarity, "
        "tag overlap, geographic proximity, and recent activity. Results include interaction "
        "summaries showing how others have engaged with each recommended entity."
    ),
)
async def get_recommendations(
    entity_id: uuid.UUID,
    db: DbDep,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    min_score: float = Query(default=0.1, ge=0.0, le=1.0),
    entity_type: Optional[str] = Query(default=None, description="project | organisation"),
    category_filter: Optional[str] = Query(default=None),
    geo_only: bool = Query(default=False, description="Restrict to same region"),
    include_explanation: bool = Query(default=False, description="Include score breakdown"),
):
    svc = RecommendationOrchestrator(db)
    return await svc.get_recommendations(
        entity_id=entity_id,
        limit=limit,
        page=page,
        min_score=min_score,
        entity_type=entity_type,
        category_filter=category_filter,
        geo_only=geo_only,
        include_explanation=include_explanation,
    )


@router.get(
    "/similar/{entity_id}",
    response_model=SimilarResponse,
    summary="Find semantically similar entities",
    description=(
        "Returns entities most semantically similar to the given one, "
        "ignoring geographic constraints. Useful for cross-region discovery."
    ),
)
async def get_similar(
    entity_id: uuid.UUID,
    db: DbDep,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
    svc = RecommendationOrchestrator(db)
    return await svc.get_similar(entity_id=entity_id, limit=limit, page=page)


@router.post(
    "/recommendations/{entity_id}/feedback",
    summary="Record user feedback on a recommendation",
    status_code=status.HTTP_201_CREATED,
)
async def record_feedback(
    entity_id: uuid.UUID,
    body: FeedbackRequest,
    db: DbDep,
    user: CurrentUser,
) -> dict:
    """
    Record how the current user feels about a recommendation.

    signal values:
      helpful     — recommendation was relevant and useful
      not_helpful — recommendation was irrelevant
      dismissed   — user does not want to see this again
    """
    if body.signal not in _FEEDBACK_SIGNALS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"signal must be one of: {sorted(_FEEDBACK_SIGNALS)}",
        )

    repo     = EntityRepository(db)
    actor_id = uuid.UUID(user["sub"])
    event_type = _FEEDBACK_EVENT_TYPES[body.signal]

    # Replace any existing feedback from this user on this entity
    existing = await repo.get_feedback_activity(
        entity_id, actor_id, list(_FEEDBACK_EVENT_TYPES.values())
    )
    if existing:
        await repo.delete_activity_by_id(existing.id)

    event = ActivityEvent(
        entity_id=entity_id,
        event_type=event_type,
        actor_id=actor_id,
        occurred_at=datetime.now(timezone.utc),
        payload={"signal": body.signal},
    )
    await repo.add_activity(event)
    await db.commit()

    return {
        "entity_id":  str(entity_id),
        "signal":     body.signal,
        "event_type": event_type,
        "recorded_at": event.occurred_at.isoformat(),
    }


@router.delete(
    "/recommendations/{entity_id}/feedback",
    summary="Retract user feedback on a recommendation",
    status_code=status.HTTP_200_OK,
)
async def retract_feedback(
    entity_id: uuid.UUID,
    db: DbDep,
    user: CurrentUser,
) -> dict:
    """
    Remove any previously recorded feedback (helpful/not_helpful/dismissed)
    for the current user on this entity.
    """
    repo     = EntityRepository(db)
    actor_id = uuid.UUID(user["sub"])

    existing = await repo.get_feedback_activity(
        entity_id, actor_id, list(_FEEDBACK_EVENT_TYPES.values())
    )
    if not existing:
        return {"message": "No feedback found to retract.", "entity_id": str(entity_id)}

    await repo.delete_activity_by_id(existing.id)
    await db.commit()

    return {
        "message":   "Feedback retracted.",
        "entity_id": str(entity_id),
        "signal":    existing.payload.get("signal") if existing.payload else None,
    }


@router.get(
    "/recommendations/dismissed",
    summary="List entities the current user has dismissed",
)
async def list_dismissed(
    db: DbDep,
    user: CurrentUser,
    page: int  = Query(default=1, ge=1),
    size: int  = Query(default=50, ge=1, le=200),
) -> dict:
    """Returns entity IDs the current user has marked as dismissed."""
    from sqlalchemy import select
    actor_id = uuid.UUID(user["sub"])
    result = await db.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.event_type == "recommendation_dismissed",
            ActivityEvent.actor_id == actor_id,
        )
        .order_by(ActivityEvent.occurred_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    events = result.scalars().all()
    return {
        "dismissed": [
            {"entity_id": str(e.entity_id), "dismissed_at": e.occurred_at.isoformat()}
            for e in events
        ],
        "page":  page,
        "count": len(events),
    }
