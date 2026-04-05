"""schemas/recommendation.py — Request/response models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Response models ───────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    semantic: float = 0.0
    tag_overlap: float = 0.0
    geo_proximity: float = 0.0
    recency: float = 0.0


class InteractionSummary(BaseModel):
    """How others have interacted with this entity."""
    feedback_count: int = 0
    grievance_count: int = 0
    suggestion_count: int = 0
    applause_count: int = 0
    engagement_count: int = 0


class RecommendedEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: uuid.UUID
    entity_type: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    cover_image_url: Optional[str] = None
    org_logo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country_code: Optional[str] = None
    status: str = "active"

    score: float = 0.0
    score_breakdown: Optional[ScoreBreakdown] = None
    distance_km: Optional[float] = None
    shared_tags: List[str] = []

    interactions: Optional[InteractionSummary] = None

    accepts_grievances: bool = True
    accepts_suggestions: bool = True
    accepts_applause: bool = True


class RecommendationResponse(BaseModel):
    entity_id: uuid.UUID
    recommendations: List[RecommendedEntity]
    total: int
    page: int = 1
    page_size: int = 20
    generated_at: datetime
    cache_hit: bool = False


class NearbyResponse(BaseModel):
    latitude: float
    longitude: float
    radius_km: float
    results: List[RecommendedEntity]
    total: int
    page: int = 1
    page_size: int = 20
    generated_at: datetime


class SimilarResponse(BaseModel):
    entity_id: uuid.UUID
    similar: List[RecommendedEntity]
    total: int
    page: int = 1
    page_size: int = 20
    generated_at: datetime


# ── Request models (for indexing) ─────────────────────────────────────────────

class IndexEntityRequest(BaseModel):
    entity_id: uuid.UUID
    entity_type: str = "project"
    source_service: str = "riviwa_auth_service"
    organisation_id: Optional[uuid.UUID] = None
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    tags: Optional[List[str]] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    primary_lga: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    status: str = "active"
    cover_image_url: Optional[str] = None
    org_logo_url: Optional[str] = None
    accepts_grievances: bool = True
    accepts_suggestions: bool = True
    accepts_applause: bool = True


class IndexActivityRequest(BaseModel):
    entity_id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID] = None
    feedback_type: Optional[str] = None
    occurred_at: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    database: bool
    qdrant: bool
    redis: bool
    embedding_model_loaded: bool
