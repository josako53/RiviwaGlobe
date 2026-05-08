"""schemas/staff_fraud_report.py — Fraud report request/response schemas."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Submit Fraud Report (multipart) ──────────────────────────────────────────

class FraudReportOut(BaseModel):
    id: UUID
    verification_event_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    reporter_email: Optional[str] = None
    claimed_staff_name: Optional[str] = None
    claimed_staff_id: Optional[str] = None
    description: str
    photo_urls: Optional[List[Any]] = None
    status: str
    ai_analysis: Optional[Dict[str, Any]] = None
    assigned_agent_id: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class FraudReportUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    resolution_notes: Optional[str] = None

    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"SUBMITTED", "UNDER_INVESTIGATION", "CONFIRMED_FRAUD", "DISMISSED", "RESOLVED"}
        if v.upper() not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v.upper()


class FraudReportAssignRequest(BaseModel):
    agent_user_id: UUID
    notes: Optional[str] = None


class FraudReportListOut(BaseModel):
    items: List[FraudReportOut]
    total: int
    page: int
    size: int
    pages: int
