from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UrgencyRequestIn(BaseModel):
    urgency_type:   str           = Field(..., description="MEDICAL|FINANCIAL|TIME_SENSITIVE|OTHER")
    evidence_notes: Optional[str] = Field(default=None, max_length=1000)


class UrgencyRequestOut(BaseModel):
    id:             uuid.UUID
    ticket_id:      uuid.UUID
    org_id:         uuid.UUID
    urgency_type:   str
    evidence_notes: Optional[str]
    status:         str
    requested_at:   datetime
    reviewed_at:    Optional[datetime]
    reviewer_notes: Optional[str]

    model_config = {"from_attributes": True}


class UrgencyReviewIn(BaseModel):
    status:         str           = Field(..., description="APPROVED|REJECTED")
    reviewer_notes: Optional[str] = None
