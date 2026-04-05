"""api/v1/discover.py — Location-scoped discovery endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.dependencies import CurrentUser, DbDep
from schemas.recommendation import NearbyResponse
from services.recommendation_service import RecommendationOrchestrator

router = APIRouter(tags=["Discovery"])


@router.get(
    "/discover/nearby",
    response_model=NearbyResponse,
    summary="Discover entities near a location",
    description=(
        "Returns entities near the given coordinates, sorted by distance. "
        "Each result includes interaction summaries showing grievances, "
        "suggestions, and applause from other users."
    ),
)
async def discover_nearby(
    db: DbDep,
    user: CurrentUser,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=50.0, ge=1, le=5000),
    entity_type: Optional[str] = Query(default=None, description="project | organisation"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
    svc = RecommendationOrchestrator(db)
    return await svc.discover_nearby(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        entity_type=entity_type,
        category=category,
        limit=limit,
        page=page,
    )
