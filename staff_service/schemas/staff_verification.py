"""schemas/staff_verification.py — Verification request/response schemas."""
from __future__ import annotations

import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from schemas.staff_profile import StaffPublicOut


# ── Verify Request / Response ─────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    code: str
    scanner_lat: Optional[float] = None
    scanner_lng: Optional[float] = None
    user_agent: Optional[str] = None


class VerifyResponse(BaseModel):
    result: str  # VALID | INVALID | SUSPENDED | TERMINATED | ON_LEAVE
    verification_event_id: UUID
    staff: Optional[StaffPublicOut] = None
    message: str
    feedback_url: Optional[str] = None


# ── Admin List ────────────────────────────────────────────────────────────────

class VerificationEventOut(BaseModel):
    id: UUID
    lookup_code: str
    staff_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    result: str
    scanner_lat: Optional[float] = None
    scanner_lng: Optional[float] = None
    scanner_ip: Optional[str] = None
    user_agent: Optional[str] = None
    verified_at: dt.datetime

    model_config = {"from_attributes": True}


class VerificationListOut(BaseModel):
    items: List[VerificationEventOut]
    total: int
    page: int
    size: int
    pages: int
