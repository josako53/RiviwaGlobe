from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StaffCounterCreate(BaseModel):
    org_id:           uuid.UUID
    service_point_id: uuid.UUID
    name:             str  = Field(..., max_length=150)
    code:             str  = Field(..., max_length=20)
    user_id:          Optional[uuid.UUID] = None


class StaffCounterUpdate(BaseModel):
    name:      Optional[str]       = Field(default=None, max_length=150)
    code:      Optional[str]       = Field(default=None, max_length=20)
    user_id:   Optional[uuid.UUID] = None
    is_active: Optional[bool]      = None


class StaffCounterOut(BaseModel):
    id:                uuid.UUID
    org_id:            uuid.UUID
    service_point_id:  uuid.UUID
    name:              str
    code:              str
    user_id:           Optional[uuid.UUID]
    is_active:         bool
    is_available:      bool
    current_ticket_id: Optional[uuid.UUID]
    created_at:        datetime
    updated_at:        datetime

    model_config = {"from_attributes": True}


class OpenSessionIn(BaseModel):
    staff_counter_id: uuid.UUID


class SessionOut(BaseModel):
    id:                  uuid.UUID
    staff_counter_id:    uuid.UUID
    org_id:              uuid.UUID
    service_point_id:    uuid.UUID
    opened_at:           datetime
    closed_at:           Optional[datetime]
    is_active:           bool
    tickets_served:      int
    avg_service_seconds: float

    model_config = {"from_attributes": True}
