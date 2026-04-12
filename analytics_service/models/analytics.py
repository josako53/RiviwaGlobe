"""models/analytics.py — SQLModel ORM models for analytics_db tables."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

log = structlog.get_logger(__name__)


class StaffLogin(SQLModel, table=True):
    """Records each staff member login event for activity tracking."""
    __tablename__ = "staff_logins"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True, nullable=False)
    login_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    ip_address: Optional[str] = Field(default=None, max_length=50)
    platform: Optional[str] = Field(default=None, max_length=50)


class FeedbackSLAStatus(SQLModel, table=True):
    """Pre-computed SLA compliance status for each feedback item."""
    __tablename__ = "feedback_sla_status"

    feedback_id: UUID = Field(primary_key=True)
    project_id: UUID = Field(index=True, nullable=False)
    feedback_type: str = Field(max_length=50)
    priority: str = Field(max_length=20)
    submitted_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    ack_deadline: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    res_deadline: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    ack_sla_met: Optional[bool] = Field(default=None)
    res_sla_met: Optional[bool] = Field(default=None)
    ack_sla_breached: bool = Field(default=False, index=True)
    res_sla_breached: bool = Field(default=False, index=True)
    days_unresolved: Optional[float] = Field(default=None)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )


class HotspotAlert(SQLModel, table=True):
    """Tracks geographic/category spikes in feedback volume."""
    __tablename__ = "hotspot_alerts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(index=True, nullable=False)
    location: str = Field(max_length=200)
    category: str = Field(max_length=100)
    count_in_window: int = Field(nullable=False)
    baseline_avg: float = Field(nullable=False)
    spike_factor: float = Field(nullable=False)
    window_start: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    window_end: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    alert_status: str = Field(default="active", max_length=20, index=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )


class CommitteePerformance(SQLModel, table=True):
    """Daily pre-computed performance metrics per committee."""
    __tablename__ = "committee_performance"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    committee_id: UUID = Field(index=True, nullable=False)
    project_id: UUID = Field(index=True, nullable=False)
    computed_date: date = Field(index=True, nullable=False)
    cases_assigned: int = Field(default=0)
    cases_resolved: int = Field(default=0)
    cases_overdue: int = Field(default=0)
    avg_resolution_hours: Optional[float] = Field(default=None)
    resolution_rate: Optional[float] = Field(default=None)


class FeedbackMLScore(SQLModel, table=True):
    """ML-generated scores for individual feedback items."""
    __tablename__ = "feedback_ml_scores"

    feedback_id: UUID = Field(primary_key=True)
    escalation_probability: Optional[float] = Field(default=None)
    predicted_resolution_hours: Optional[float] = Field(default=None)
    recommended_priority: Optional[str] = Field(default=None, max_length=20)
    model_version: Optional[str] = Field(default=None, max_length=50)
    scored_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )


class GeneratedReport(SQLModel, table=True):
    """Metadata for generated analytics reports stored in object storage."""
    __tablename__ = "generated_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(index=True, nullable=False)
    report_type: str = Field(max_length=100, index=True)
    period_start: Optional[date] = Field(default=None)
    period_end: Optional[date] = Field(default=None)
    file_url: Optional[str] = Field(default=None, max_length=500)
    file_format: Optional[str] = Field(default=None, max_length=20)
    generated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )
