from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ServicePointStats(BaseModel):
    service_point_id:    uuid.UUID
    service_point_name:  str
    point_type:          str
    waiting_count:       int
    attending_count:     int
    avg_wait_seconds:    Optional[float]
    avg_service_seconds: Optional[float]
    throughput_today:    int

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    org_id:                uuid.UUID
    generated_at:          datetime
    total_waiting:         int
    total_attending:       int
    total_completed_today: int
    service_points:        List[ServicePointStats]


# ── Staff duty sessions ───────────────────────────────────────────────────────

class StaffDutyItem(BaseModel):
    session_id:          uuid.UUID
    staff_user_id:       Optional[uuid.UUID]
    counter_name:        Optional[str]
    counter_code:        Optional[str]
    service_point_id:    Optional[uuid.UUID]
    service_point_name:  Optional[str]
    point_type:          Optional[str]
    opened_at:           Optional[datetime]
    closed_at:           Optional[datetime]
    is_active:           bool
    tickets_served:      int
    avg_service_seconds: Optional[float]


class StaffDutyOut(BaseModel):
    org_id:          uuid.UUID
    date_from:       str
    date_to:         str
    total_sessions:  int
    active_sessions: int
    items:           List[StaffDutyItem]


# ── Wait time by period ───────────────────────────────────────────────────────

class WaitByPeriodItem(BaseModel):
    period:               Optional[datetime]
    tickets_served:       int
    avg_wait_seconds:     Optional[float]
    avg_service_seconds:  Optional[float]
    min_wait_seconds:     Optional[float]
    max_wait_seconds:     Optional[float]


class WaitByPeriodOut(BaseModel):
    org_id:      uuid.UUID
    granularity: str
    date_from:   str
    date_to:     str
    items:       List[WaitByPeriodItem]


# ── Wait time by service point ────────────────────────────────────────────────

class ServicePointWaitItem(BaseModel):
    service_point_id:    uuid.UUID
    service_point_name:  str
    point_type:          str
    tickets_served:      int
    avg_wait_seconds:    Optional[float]
    avg_service_seconds: Optional[float]
    max_wait_seconds:    Optional[float]
    min_wait_seconds:    Optional[float]


class ServicePointWaitOut(BaseModel):
    org_id:    uuid.UUID
    date_from: str
    date_to:   str
    items:     List[ServicePointWaitItem]
