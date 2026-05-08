"""schemas/staff_profile.py — Staff profile request/response schemas."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Public view (safe for unauthenticated callers) ────────────────────────────

class StaffPublicOut(BaseModel):
    """Subset of staff info returned on a VALID verification scan."""
    staff_code: str
    display_name: str
    position: str
    department: Optional[str] = None
    branch_name: Optional[str] = None
    employment_type: str
    is_verified: bool
    photo_url: Optional[str] = None
    org_id: UUID
    expertise: Optional[List[Any]] = None
    hire_year: Optional[int] = None  # Only the year of hire_date, for privacy

    model_config = {"from_attributes": True}


# ── Admin: Create / Update ─────────────────────────────────────────────────────

class StaffProfileCreate(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    badge_number: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    position: str = Field(..., max_length=200)
    department: Optional[str] = Field(None, max_length=200)
    branch_id: Optional[UUID] = None
    branch_name: Optional[str] = Field(None, max_length=200)
    supervisor_id: Optional[UUID] = None
    employment_type: str = Field(default="FULL_TIME", max_length=20)
    expertise: Optional[List[str]] = None
    bio: Optional[str] = None
    id_number: Optional[str] = Field(None, max_length=100)
    project_ids: Optional[List[UUID]] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    hire_date: Optional[dt.date] = None
    qr_code_id: Optional[UUID] = None

    @field_validator("employment_type")
    @classmethod
    def validate_employment_type(cls, v: str) -> str:
        allowed = {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERN", "VOLUNTEER"}
        if v.upper() not in allowed:
            raise ValueError(f"employment_type must be one of {allowed}")
        return v.upper()

    model_config = {"populate_by_name": True}


class StaffProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    badge_number: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=200)
    branch_id: Optional[UUID] = None
    branch_name: Optional[str] = Field(None, max_length=200)
    supervisor_id: Optional[UUID] = None
    employment_type: Optional[str] = Field(None, max_length=20)
    expertise: Optional[List[str]] = None
    bio: Optional[str] = None
    id_number: Optional[str] = Field(None, max_length=100)
    project_ids: Optional[List[UUID]] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    hire_date: Optional[dt.date] = None
    qr_code_id: Optional[UUID] = None

    @field_validator("employment_type")
    @classmethod
    def validate_employment_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERN", "VOLUNTEER"}
        if v.upper() not in allowed:
            raise ValueError(f"employment_type must be one of {allowed}")
        return v.upper()

    model_config = {"populate_by_name": True}


# ── Admin: Full Response ───────────────────────────────────────────────────────

class StaffProfileOut(BaseModel):
    id: UUID
    org_id: UUID
    staff_code: str
    qr_code_id: Optional[UUID] = None
    badge_number: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    display_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    position: str
    department: Optional[str] = None
    branch_id: Optional[UUID] = None
    branch_name: Optional[str] = None
    supervisor_id: Optional[UUID] = None
    employment_type: str
    status: str
    expertise: Optional[List[Any]] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    id_number: Optional[str] = None
    project_ids: Optional[List[Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata_")
    is_verified: bool
    hire_date: Optional[dt.date] = None
    suspension_reason: Optional[str] = None
    termination_reason: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class StaffProfileWithStats(StaffProfileOut):
    feedback_count: int = 0
    avg_rating: Optional[float] = None


# ── Suspend / Terminate / Reinstate ───────────────────────────────────────────

class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=5)


class TerminateRequest(BaseModel):
    reason: str = Field(..., min_length=5)


# ── List / Pagination ─────────────────────────────────────────────────────────

class StaffProfileListOut(BaseModel):
    items: List[StaffProfileOut]
    total: int
    page: int
    size: int
    pages: int
