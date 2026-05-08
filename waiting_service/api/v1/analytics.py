from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query

from core.dependencies import AdminDep, DbDep, RedisDep, StaffDep
from repositories.analytics_repository import AnalyticsRepository
from schemas.analytics import (
    DashboardOut,
    ServicePointWaitItem,
    ServicePointWaitOut,
    StaffDutyItem,
    StaffDutyOut,
    WaitByPeriodItem,
    WaitByPeriodOut,
)
from services.analytics_service import AnalyticsService

analytics_router = APIRouter(prefix="/waiting/analytics", tags=["Analytics"])


def _window(date_from: Optional[str], date_to: Optional[str], default_days: int = 1):
    now = datetime.now(timezone.utc)
    dt_from = (
        datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        if date_from
        else (now - timedelta(days=default_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    dt_to = (
        datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        if date_to
        else now
    )
    return dt_from, dt_to


@analytics_router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    org_id: uuid.UUID = Query(...),
    db:     DbDep     = ...,
    redis:  RedisDep  = ...,
    token:  StaffDep  = ...,
):
    return await AnalyticsService(db, redis).get_dashboard(org_id, token)


@analytics_router.get("/staff-duty", response_model=StaffDutyOut)
async def get_staff_duty(
    org_id:    uuid.UUID      = Query(...),
    date_from: Optional[str]  = Query(None, description="YYYY-MM-DD (default: today)"),
    date_to:   Optional[str]  = Query(None, description="YYYY-MM-DD (default: now)"),
    is_active: Optional[bool] = Query(None, description="true = currently active sessions only"),
    db:    DbDep    = ...,
    token: AdminDep = ...,
):
    """
    Returns all staff duty sessions: who was on duty, at which counter and
    service point, when they started/ended, and their ticket throughput.
    """
    if token.org_id and token.org_id != org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError()
    dt_from, dt_to = _window(date_from, date_to, default_days=1)
    repo = AnalyticsRepository(db)
    rows = await repo.get_staff_duty_sessions(org_id, dt_from, dt_to, is_active)
    items = [
        StaffDutyItem(
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
            avg_service_seconds= float(r["avg_service_seconds"]) if r.get("avg_service_seconds") is not None else None,
        )
        for r in rows
    ]
    return StaffDutyOut(
        org_id=org_id,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        total_sessions=len(items),
        active_sessions=sum(1 for i in items if i.is_active),
        items=items,
    )


@analytics_router.get("/by-period", response_model=WaitByPeriodOut)
async def get_by_period(
    org_id:      uuid.UUID     = Query(...),
    granularity: str           = Query("hour", description="hour | day | week"),
    date_from:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:     Optional[str] = Query(None, description="YYYY-MM-DD"),
    db:    DbDep    = ...,
    token: AdminDep = ...,
):
    """
    Queue wait and service times bucketed by period.
    granularity=hour: intra-day (set 1–3 day range).
    granularity=day: weekly/monthly trend.
    """
    if token.org_id and token.org_id != org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError()
    if granularity not in ("hour", "day", "week"):
        granularity = "hour"
    default_days = 1 if granularity == "hour" else 7
    dt_from, dt_to = _window(date_from, date_to, default_days)
    repo = AnalyticsRepository(db)
    rows = await repo.get_wait_time_by_period(org_id, dt_from, dt_to, granularity)
    items = [
        WaitByPeriodItem(
            period              = r.get("period"),
            tickets_served      = int(r.get("tickets_served") or 0),
            avg_wait_seconds    = float(r["avg_wait_seconds"]) if r.get("avg_wait_seconds") is not None else None,
            avg_service_seconds = float(r["avg_service_seconds"]) if r.get("avg_service_seconds") is not None else None,
            min_wait_seconds    = float(r["min_wait_seconds"]) if r.get("min_wait_seconds") is not None else None,
            max_wait_seconds    = float(r["max_wait_seconds"]) if r.get("max_wait_seconds") is not None else None,
        )
        for r in rows
    ]
    return WaitByPeriodOut(
        org_id=org_id,
        granularity=granularity,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        items=items,
    )


@analytics_router.get("/by-service-point", response_model=ServicePointWaitOut)
async def get_by_service_point(
    org_id:    uuid.UUID     = Query(...),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD (default: 7 days ago)"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD (default: now)"),
    db:    DbDep    = ...,
    token: AdminDep = ...,
):
    """
    Wait and service time aggregated per service point.
    Shows which service points have the longest queues over the period.
    """
    if token.org_id and token.org_id != org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError()
    dt_from, dt_to = _window(date_from, date_to, default_days=7)
    repo = AnalyticsRepository(db)
    rows = await repo.get_wait_by_service_point(org_id, dt_from, dt_to)
    items = [
        ServicePointWaitItem(
            service_point_id    = r["service_point_id"],
            service_point_name  = r["service_point_name"],
            point_type          = r["point_type"],
            tickets_served      = int(r.get("tickets_served") or 0),
            avg_wait_seconds    = float(r["avg_wait_seconds"]) if r.get("avg_wait_seconds") is not None else None,
            avg_service_seconds = float(r["avg_service_seconds"]) if r.get("avg_service_seconds") is not None else None,
            max_wait_seconds    = float(r["max_wait_seconds"]) if r.get("max_wait_seconds") is not None else None,
            min_wait_seconds    = float(r["min_wait_seconds"]) if r.get("min_wait_seconds") is not None else None,
        )
        for r in rows
    ]
    return ServicePointWaitOut(
        org_id=org_id,
        date_from=dt_from.date().isoformat(),
        date_to=dt_to.date().isoformat(),
        items=items,
    )
