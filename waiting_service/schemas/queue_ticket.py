from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JoinQueueIn(BaseModel):
    org_id:         uuid.UUID
    flow_id:        uuid.UUID
    phone_number:   Optional[str] = Field(default=None, max_length=20)
    submitter_name: Optional[str] = Field(default=None, max_length=200)
    channel:        str           = Field(default="KIOSK", description="KIOSK|SMS|APP|STAFF_RECORDED")
    priority:       str           = Field(default="NORMAL", description="NORMAL|HIGH|URGENT")
    external_id:    Optional[str] = Field(default=None, max_length=200)
    notes:          Optional[str] = None


class StageOut(BaseModel):
    id:                       uuid.UUID
    service_point_id:         uuid.UUID
    step_order:               int
    status:                   str
    staff_counter_id:         Optional[uuid.UUID]
    assigned_staff_user_id:   Optional[uuid.UUID]
    entered_queue_at:         datetime
    attending_started_at:     Optional[datetime]
    finished_at:              Optional[datetime]
    wait_duration_seconds:    Optional[float]
    service_duration_seconds: Optional[float]

    model_config = {"from_attributes": True}


class TicketStatusOut(BaseModel):
    id:                       uuid.UUID
    ticket_number:            str
    org_id:                   uuid.UUID
    flow_id:                  uuid.UUID
    current_service_point_id: uuid.UUID
    current_step_order:       int
    status:                   str
    priority:                 int
    channel:                  str
    eta_minutes:              Optional[float]
    position_in_queue:        Optional[int]
    created_at:               datetime
    completed_at:             Optional[datetime]
    current_stage:            Optional[StageOut]

    model_config = {"from_attributes": True}


class CallNextOut(BaseModel):
    ticket_number:      str
    submitter_name:     Optional[str]
    phone_number:       Optional[str]
    position_was:       int
    service_point_name: str
    staff_counter_name: str


class FinishOut(BaseModel):
    ticket_number:           str
    status:                  str
    next_service_point_id:   Optional[uuid.UUID]
    next_service_point_name: Optional[str]
    is_final_step:           bool


class SetPriorityIn(BaseModel):
    priority: str           = Field(..., description="NORMAL|HIGH|URGENT")
    reason:   Optional[str] = None
