"""
models/entity.py — SQLModel tables for recommendation index.

RecommendationEntity: local cache of recommendable entities (projects, orgs, etc.)
ActivityEvent: raw activity signals from Kafka (feedback, engagement, etc.)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RecommendationEntity(SQLModel, table=True):
    """
    Local index of entities available for recommendation.
    Sourced from org_project events, org events, etc.
    """
    __tablename__ = "rec_entities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────────
    entity_type: str = Field(max_length=50, nullable=False, index=True)
    source_service: str = Field(max_length=100, nullable=False, default="riviwa_auth_service")
    organisation_id: Optional[uuid.UUID] = Field(default=None, index=True)

    name: str = Field(max_length=255, nullable=False)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # ── Classification ────────────────────────────────────────────────────────
    category: Optional[str] = Field(default=None, max_length=100, index=True)
    sector: Optional[str] = Field(default=None, max_length=100, index=True)
    tags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    # ── Location ──────────────────────────────────────────────────────────────
    country_code: Optional[str] = Field(default=None, max_length=5)
    region: Optional[str] = Field(default=None, max_length=100, index=True)
    primary_lga: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)

    # ── Status & metadata ─────────────────────────────────────────────────────
    status: str = Field(default="active", max_length=30, index=True)
    cover_image_url: Optional[str] = Field(default=None, max_length=512)
    org_logo_url: Optional[str] = Field(default=None, max_length=512)

    # ── Interaction signals ───────────────────────────────────────────────────
    feedback_count: int = Field(default=0)
    grievance_count: int = Field(default=0)
    suggestion_count: int = Field(default=0)
    applause_count: int = Field(default=0)
    engagement_count: int = Field(default=0)

    # ── Embedding tracking ────────────────────────────────────────────────────
    is_indexed: bool = Field(default=False)
    embedding_text_hash: Optional[str] = Field(default=None, max_length=64)

    # ── Timestamps ────────────────────────────────────────────────────────────
    last_active_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # ── Accepts flags (from project) ─────────────────────────────────────────
    accepts_grievances: bool = Field(default=True)
    accepts_suggestions: bool = Field(default=True)
    accepts_applause: bool = Field(default=True)


class ActivityEvent(SQLModel, table=True):
    """
    Raw activity signals consumed from Kafka.
    Used to compute popularity/recency scores.
    """
    __tablename__ = "rec_activity_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    entity_id: uuid.UUID = Field(nullable=False, index=True)
    event_type: str = Field(max_length=100, nullable=False, index=True)
    actor_id: Optional[uuid.UUID] = Field(default=None)
    feedback_type: Optional[str] = Field(default=None, max_length=50)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
