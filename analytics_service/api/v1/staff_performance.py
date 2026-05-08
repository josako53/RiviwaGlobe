"""
api/v1/staff_performance.py
────────────────────────────────────────────────────────────────────────────
Cross-service staff performance analytics — joins waiting_db (duty sessions,
wait times) with feedback_db (grievances, suggestions, applause, inquiries)
so managers can see, for any period:

  • Which staff were on duty and at which service point
  • Average queue wait time each staff member created
  • How many of each feedback type arrived during their duty window
  • When during the day/week feedback volume peaks (heatmap)
  • Correlation: high wait time periods → elevated grievance volume
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import (
    FeedbackDbDep,
    OrgAdminDep,
    WaitingDbDep,
    assert_org_access,
)
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from repositories.waiting_analytics_repo import WaitingAnalyticsRepository
from schemas.staff_performance import (
    FeedbackTimingCell,
    FeedbackTimingResponse,
    StaffDutyResponse,
    StaffDutySessionItem,
    StaffPerformanceItem,
    StaffPerformanceResponse,
    WaitingFeedbackPeriodItem,
    WaitingVsFeedbackResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/org", tags=["Analytics — Staff Performance"])

_DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _parse_window(
    date_from: Optional[str],
    date_to: Optional[str],
    default_days: int = 7,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if date_from:
        dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    else:
        dt_from = (now - timedelta(days=default_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    if date_to:
        dt_to = datetime.fromisoformat(date_to).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    else:
        dt_to = now
    return dt_from, dt_to


# ── GET /analytics/org/{org_id}/staff-performance ────────────────────────────

@router.get("/{org_id}/staff-performance", response_model=StaffPerformanceResponse)
async def get_staff_performance(
    org_id:           UUID,
    date_from:        Optional[str]  = Query(None, description="YYYY-MM-DD — start of window (default: 7 days ago)"),
    date_to:          Optional[str]  = Query(None, description="YYYY-MM-DD — end of window (default: now)"),
    service_point_id: Optional[UUID] = Query(None, description="Filter to a specific service point"),
    token: OrgAdminDep  = None,
    w_db:  WaitingDbDep = None,
    fb_db: FeedbackDbDep= None,
) -> StaffPerformanceResponse:
    """
    Per-staff performance combining queue metrics with feedback volume.

    For each staff member who served customers in the period, returns:
    - Service point, tickets served, avg/min/max wait time, avg service time
    - Total feedback (and breakdown by type) submitted to the org during
      that staff member's active duty window (first_attended → last_finished)

    This reveals: Staff X served 45 customers with avg 8-min wait, and
    during their shift 12 grievances and 3 applause were filed.
    """
    assert_org_access(token, org_id)
    dt_from, dt_to = _parse_window(date_from, date_to, default_days=7)

    w_repo  = WaitingAnalyticsRepository(w_db)
    fb_repo = FeedbackAnalyticsRepository(fb_db)

    staff_rows = await w_repo.get_staff_performance(org_id, dt_from, dt_to, service_point_id)

    items: list[StaffPerformanceItem] = []
    for row in staff_rows:
        first_at = row.get("first_attended_at") or dt_from
        last_at  = row.get("last_finished_at")  or dt_to
        if isinstance(first_at, str):
            first_at = datetime.fromisoformat(first_at)
        if isinstance(last_at, str):
            last_at = datetime.fromisoformat(last_at)
        if first_at.tzinfo is None:
            first_at = first_at.replace(tzinfo=timezone.utc)
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)

        fb = await fb_repo.get_feedback_counts_in_window(org_id, first_at, last_at)

        items.append(StaffPerformanceItem(
            staff_user_id       = row["staff_user_id"],
            service_point_id    = row.get("service_point_id"),
            service_point_name  = row.get("service_point_name"),
            point_type          = row.get("point_type"),
            tickets_served      = int(row.get("tickets_served") or 0),
            avg_wait_seconds    = _f(row.get("avg_wait_seconds")),
            avg_service_seconds = _f(row.get("avg_service_seconds")),
            min_wait_seconds    = _f(row.get("min_wait_seconds")),
            max_wait_seconds    = _f(row.get("max_wait_seconds")),
            first_attended_at   = first_at,
            last_finished_at    = last_at,
            feedback_total      = int(fb.get("total") or 0),
            feedback_grievances = int(fb.get("grievances") or 0),
            feedback_suggestions= int(fb.get("suggestions") or 0),
            feedback_applause   = int(fb.get("applause") or 0),
            feedback_inquiries  = int(fb.get("inquiries") or 0),
        ))

    return StaffPerformanceResponse(
        org_id=org_id,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        total_staff=len(items),
        items=items,
    )


# ── GET /analytics/org/{org_id}/staff-duty ───────────────────────────────────

@router.get("/{org_id}/staff-duty", response_model=StaffDutyResponse)
async def get_staff_duty(
    org_id:    UUID,
    date_from: Optional[str]  = Query(None, description="YYYY-MM-DD (default: today)"),
    date_to:   Optional[str]  = Query(None, description="YYYY-MM-DD (default: now)"),
    is_active: Optional[bool] = Query(None, description="true = currently active sessions only"),
    token: OrgAdminDep  = None,
    w_db:  WaitingDbDep = None,
) -> StaffDutyResponse:
    """
    Shows all staff duty sessions in a period: who was on duty, at which
    counter and service point, when they opened/closed, and throughput.

    Use is_active=true to see who is currently serving customers right now.
    """
    assert_org_access(token, org_id)
    dt_from, dt_to = _parse_window(date_from, date_to, default_days=1)

    w_repo = WaitingAnalyticsRepository(w_db)
    rows   = await w_repo.get_staff_duty_sessions(org_id, dt_from, dt_to, is_active)

    items = [
        StaffDutySessionItem(
            session_id         = r["session_id"],
            staff_user_id      = r.get("staff_user_id"),
            counter_name       = r.get("counter_name"),
            counter_code       = r.get("counter_code"),
            service_point_id   = r.get("service_point_id"),
            service_point_name = r.get("service_point_name"),
            point_type         = r.get("point_type"),
            opened_at          = r.get("opened_at"),
            closed_at          = r.get("closed_at"),
            is_active          = bool(r.get("is_active", False)),
            tickets_served     = int(r.get("tickets_served") or 0),
            avg_service_seconds= _f(r.get("avg_service_seconds")),
        )
        for r in rows
    ]

    return StaffDutyResponse(
        org_id=org_id,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        total_sessions=len(items),
        active_sessions=sum(1 for i in items if i.is_active),
        items=items,
    )


# ── GET /analytics/org/{org_id}/waiting-vs-feedback ──────────────────────────

@router.get("/{org_id}/waiting-vs-feedback", response_model=WaitingVsFeedbackResponse)
async def get_waiting_vs_feedback(
    org_id:        UUID,
    granularity:   str           = Query("hour", description="hour | day | week"),
    date_from:     Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="YYYY-MM-DD"),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY"),
    token: OrgAdminDep  = None,
    w_db:  WaitingDbDep = None,
    fb_db: FeedbackDbDep= None,
) -> WaitingVsFeedbackResponse:
    """
    Side-by-side view of queue wait time vs. feedback volume for each time period.

    Reveals the correlation between long wait times and complaint spikes.
    Example insight: 'Between 10:00–11:00, avg wait was 22 min and 8 grievances
    were filed; between 14:00–15:00 wait was 4 min and only 1 grievance.'

    Use granularity=hour for intra-day analysis (set date range to 1–3 days).
    Use granularity=day for weekly/monthly trend analysis.
    """
    assert_org_access(token, org_id)
    if granularity not in ("hour", "day", "week"):
        granularity = "hour"
    default_days = 1 if granularity == "hour" else 7
    dt_from, dt_to = _parse_window(date_from, date_to, default_days)

    w_repo  = WaitingAnalyticsRepository(w_db)
    fb_repo = FeedbackAnalyticsRepository(fb_db)

    wait_rows = await w_repo.get_wait_time_by_period(org_id, dt_from, dt_to, granularity)
    fb_rows   = await fb_repo.get_feedback_by_period_for_org(
        org_id, dt_from, dt_to, granularity, feedback_type
    )

    wait_map: dict[str, dict] = {str(r.get("period")): r for r in wait_rows}
    fb_map:   dict[str, dict] = {str(r.get("period")): r for r in fb_rows}

    all_periods = sorted(set(wait_map) | set(fb_map))

    result: list[WaitingFeedbackPeriodItem] = []
    for pk in all_periods:
        w = wait_map.get(pk, {})
        f = fb_map.get(pk, {})
        result.append(WaitingFeedbackPeriodItem(
            period              = w.get("period") or f.get("period"),
            tickets_served      = int(w.get("tickets_served") or 0),
            avg_wait_seconds    = _f(w.get("avg_wait_seconds")),
            avg_service_seconds = _f(w.get("avg_service_seconds")),
            min_wait_seconds    = _f(w.get("min_wait_seconds")),
            max_wait_seconds    = _f(w.get("max_wait_seconds")),
            feedback_total      = int(f.get("total") or 0),
            feedback_grievances = int(f.get("grievances") or 0),
            feedback_suggestions= int(f.get("suggestions") or 0),
            feedback_applause   = int(f.get("applause") or 0),
            feedback_inquiries  = int(f.get("inquiries") or 0),
        ))

    return WaitingVsFeedbackResponse(
        org_id=org_id,
        granularity=granularity,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        items=result,
    )


# ── GET /analytics/org/{org_id}/feedback-timing ──────────────────────────────

@router.get("/{org_id}/feedback-timing", response_model=FeedbackTimingResponse)
async def get_feedback_timing(
    org_id:        UUID,
    date_from:     Optional[str] = Query(None, description="YYYY-MM-DD (default: 30 days ago)"),
    date_to:       Optional[str] = Query(None, description="YYYY-MM-DD (default: now)"),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY"),
    token: OrgAdminDep  = None,
    fb_db: FeedbackDbDep= None,
) -> FeedbackTimingResponse:
    """
    Feedback timing heatmap: hour-of-day × day-of-week.

    Each cell shows how many of each feedback type arrives at that hour on
    that day of the week, aggregated over the date range.

    Use this to:
    - Staff up counters before peak complaint hours
    - Schedule proactive outreach after applause peaks
    - Identify Friday afternoon inquiry spikes
    Returns peak_hour and peak_day for quick visibility.
    """
    assert_org_access(token, org_id)
    dt_from, dt_to = _parse_window(date_from, date_to, default_days=30)

    fb_repo = FeedbackAnalyticsRepository(fb_db)
    rows    = await fb_repo.get_feedback_timing_heatmap(org_id, dt_from, dt_to, feedback_type)

    cells: list[FeedbackTimingCell] = [
        FeedbackTimingCell(
            hour_of_day = int(r.get("hour_of_day") or 0),
            day_of_week = int(r.get("day_of_week") or 0),
            day_name    = _DAY_NAMES[int(r.get("day_of_week") or 0) % 7],
            total       = int(r.get("total") or 0),
            grievances  = int(r.get("grievances") or 0),
            suggestions = int(r.get("suggestions") or 0),
            applause    = int(r.get("applause") or 0),
            inquiries   = int(r.get("inquiries") or 0),
        )
        for r in rows
    ]

    peak_hour: Optional[int] = None
    peak_day:  Optional[str] = None
    if cells:
        peak = max(cells, key=lambda c: c.total)
        peak_hour = peak.hour_of_day
        peak_day  = peak.day_name

    return FeedbackTimingResponse(
        org_id=org_id,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        peak_hour=peak_hour,
        peak_day=peak_day,
        cells=cells,
    )


# ── helper ────────────────────────────────────────────────────────────────────

def _f(v: object) -> Optional[float]:
    return float(v) if v is not None else None  # type: ignore[arg-type]
