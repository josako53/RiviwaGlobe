"""models/verification.py — ORM models for the verification service."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class VerificationResult(str, Enum):
    AUTHENTIC     = "AUTHENTIC"
    ALREADY_USED  = "ALREADY_USED"
    UNRECOGNIZED  = "UNRECOGNIZED"


class ReportStatus(str, Enum):
    SUBMITTED           = "SUBMITTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    CONFIRMED_FAKE      = "CONFIRMED_FAKE"
    DISMISSED           = "DISMISSED"
    RESOLVED            = "RESOLVED"


class VerificationEvent(SQLModel, table=True):
    __tablename__ = "verification_events"

    id:              uuid.UUID         = Field(default_factory=uuid.uuid4, primary_key=True)
    short_code:      str               = Field(max_length=130, index=True)
    result:          str               = Field(sa_column=Column(String(32), nullable=False, index=True))
    qr_type:         Optional[str]     = Field(default=None, max_length=32)
    product_id:      Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    organisation_id: Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    qr_code_id:      Optional[uuid.UUID] = Field(default=None, nullable=True)
    feedback_id:     Optional[uuid.UUID] = Field(default=None, nullable=True)
    scanner_lat:     Optional[float]   = Field(default=None, nullable=True)
    scanner_lng:     Optional[float]   = Field(default=None, nullable=True)
    user_agent:      Optional[str]     = Field(default=None, max_length=512)
    product_details: Optional[Any]     = Field(default=None, sa_column=Column(JSONB, nullable=True))
    verified_at:     datetime          = Field(default_factory=datetime.utcnow, index=True)


class UnrecognizedScanHeatmap(SQLModel, table=True):
    __tablename__ = "unrecognized_scan_heatmap"

    id:                    uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    verification_event_id: uuid.UUID        = Field(foreign_key="verification_events.id", index=True)
    lat:                   float
    lng:                   float
    cluster_cell:          Optional[str]    = Field(default=None, max_length=64, index=True)
    recorded_at:           datetime         = Field(default_factory=datetime.utcnow, index=True)


class FakeSuspectReport(SQLModel, table=True):
    __tablename__ = "fake_reports"

    id:                    uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    verification_event_id: uuid.UUID        = Field(foreign_key="verification_events.id", index=True)
    short_code_scanned:    Optional[str]    = Field(default=None, max_length=130)
    reporter_phone:        Optional[str]    = Field(default=None, max_length=32)
    reporter_name:         Optional[str]    = Field(default=None, max_length=128)
    description:           Optional[str]    = Field(default=None)
    photo_key:             Optional[str]    = Field(default=None, max_length=512)
    photo_url:             Optional[str]    = Field(default=None, max_length=1024)
    gps_lat:               Optional[float]  = Field(default=None, nullable=True)
    gps_lng:               Optional[float]  = Field(default=None, nullable=True)
    location_description:  Optional[str]    = Field(default=None, max_length=512)
    status:                str              = Field(default=ReportStatus.SUBMITTED.value,
                                                   sa_column=Column(String(32), nullable=False, index=True))
    organisation_id:       Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    assigned_agent_id:     Optional[uuid.UUID] = Field(default=None, nullable=True)
    resolution_notes:      Optional[str]    = Field(default=None)
    resolved_at:           Optional[datetime] = Field(default=None, nullable=True)
    ai_analysis:           Optional[Any]    = Field(default=None, sa_column=Column(JSONB, nullable=True))
    created_at:            datetime         = Field(default_factory=datetime.utcnow, index=True)
    updated_at:            datetime         = Field(default_factory=datetime.utcnow)


class FieldAgent(SQLModel, table=True):
    __tablename__ = "field_agents"

    id:               uuid.UUID       = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id:          uuid.UUID       = Field(index=True)
    organisation_id:  uuid.UUID       = Field(index=True)
    name:             str             = Field(max_length=128)
    phone:            Optional[str]   = Field(default=None, max_length=32)
    email:            Optional[str]   = Field(default=None, max_length=256)
    is_active:        bool            = Field(default=True, index=True)
    assignment_count: int             = Field(default=0)
    created_at:       datetime        = Field(default_factory=datetime.utcnow)


class AgentAssignment(SQLModel, table=True):
    __tablename__ = "agent_assignments"

    id:            uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    fake_report_id: uuid.UUID       = Field(foreign_key="fake_reports.id", index=True)
    agent_id:      uuid.UUID        = Field(foreign_key="field_agents.id", index=True)
    assigned_by:   Optional[uuid.UUID] = Field(default=None, nullable=True)
    assigned_at:   datetime         = Field(default_factory=datetime.utcnow)
    completed_at:  Optional[datetime] = Field(default=None, nullable=True)
    notes:         Optional[str]    = Field(default=None)
