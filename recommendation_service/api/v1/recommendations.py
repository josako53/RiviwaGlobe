"""api/v1/recommendations.py — Recommendation and similarity endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.dependencies import CurrentUser, DbDep
from schemas.recommendation import RecommendationResponse, SimilarResponse
from services.recommendation_service import RecommendationOrchestrator

router = APIRouter(tags=["Recommendations"])


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
