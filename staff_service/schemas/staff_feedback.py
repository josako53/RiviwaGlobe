"""schemas/staff_feedback.py — Staff feedback request/response schemas."""
from __future__ import annotations

import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StaffFeedbackCreate(BaseModel):
    verification_event_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    service_type: Optional[str] = Field(None, max_length=200)
    location_description: Optional[str] = Field(None, max_length=500)
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    is_anonymous: bool = False
    submitter_name: Optional[str] = Field(None, max_length=200)
    submitter_phone: Optional[str] = Field(None, max_length=20)


class StaffFeedbackOut(BaseModel):
    id: UUID
    verification_event_id: UUID
    staff_id: UUID
    org_id: UUID
    rating: int
    comment: Optional[str] = None
    service_type: Optional[str] = None
    location_description: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    is_anonymous: bool
    submitter_name: Optional[str] = None
    submitter_phone: Optional[str] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class StaffFeedbackListOut(BaseModel):
    items: List[StaffFeedbackOut]
    total: int
    page: int
    size: int
    pages: int
