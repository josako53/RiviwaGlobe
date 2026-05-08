"""schemas/staff_performance.py — Response schemas for staff performance analytics."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Staff-performance per duty window ─────────────────────────────────────────

class StaffPerformanceItem(BaseModel):
    staff_user_id:        UUID
    service_point_id:     Optional[UUID]  = None
    service_point_name:   Optional[str]   = None
    point_type:           Optional[str]   = None
    tickets_served:       int             = 0
    avg_wait_seconds:     Optional[float] = None
    avg_service_seconds:  Optional[float] = None
    min_wait_seconds:     Optional[float] = None
    max_wait_seconds:     Optional[float] = None
    first_attended_at:    Optional[datetime] = None
    last_finished_at:     Optional[datetime] = None
    # Feedback submitted in the same duty window (same org, same time range)
    feedback_total:       int = 0
    feedback_grievances:  int = 0
    feedback_suggestions: int = 0
    feedback_applause:    int = 0
    feedback_inquiries:   int = 0


class StaffPerformanceResponse(BaseModel):
    org_id:       UUID
    date_from:    Optional[str] = None
    date_to:      Optional[str] = None
    total_staff:  int
    items:        List[StaffPerformanceItem]


# ── Staff duty sessions ───────────────────────────────────────────────────────

class StaffDutySessionItem(BaseModel):
    session_id:          UUID
    staff_user_id:       Optional[UUID]  = None
    counter_name:        Optional[str]   = None
    counter_code:        Optional[str]   = None
    service_point_id:    Optional[UUID]  = None
    service_point_name:  Optional[str]   = None
    point_type:          Optional[str]   = None
    opened_at:           Optional[datetime] = None
    closed_at:           Optional[datetime] = None
    is_active:           bool            = False
    tickets_served:      int             = 0
    avg_service_seconds: Optional[float] = None


class StaffDutyResponse(BaseModel):
    org_id:          UUID
    date_from:       Optional[str] = None
    date_to:         Optional[str] = None
    total_sessions:  int
    active_sessions: int
    items:           List[StaffDutySessionItem]


# ── Waiting time vs feedback correlation by period ────────────────────────────

class WaitingFeedbackPeriodItem(BaseModel):
    period:               Optional[datetime] = None
    # Queue side
    tickets_served:       int             = 0
    avg_wait_seconds:     Optional[float] = None
    avg_service_seconds:  Optional[float] = None
    min_wait_seconds:     Optional[float] = None
    max_wait_seconds:     Optional[float] = None
    # Feedback side
    feedback_total:       int = 0
    feedback_grievances:  int = 0
    feedback_suggestions: int = 0
    feedback_applause:    int = 0
    feedback_inquiries:   int = 0


class WaitingVsFeedbackResponse(BaseModel):
    org_id:      UUID
    granularity: str
    date_from:   Optional[str] = None
    date_to:     Optional[str] = None
    items:       List[WaitingFeedbackPeriodItem]


# ── Feedback timing heatmap (hour × day-of-week) ─────────────────────────────

class FeedbackTimingCell(BaseModel):
    hour_of_day:  int        # 0–23
    day_of_week:  int        # 0 = Sunday … 6 = Saturday
    day_name:     str
    total:        int = 0
    grievances:   int = 0
    suggestions:  int = 0
    applause:     int = 0
    inquiries:    int = 0


class FeedbackTimingResponse(BaseModel):
    org_id:    UUID
    date_from: Optional[str] = None
    date_to:   Optional[str] = None
    peak_hour: Optional[int] = None
    peak_day:  Optional[str] = None
    cells:     List[FeedbackTimingCell]
