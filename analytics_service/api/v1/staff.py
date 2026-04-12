"""
api/v1/staff.py — Analytics endpoints for staff activity and committee performance.
Requires Bearer JWT with org admin role (admin/owner or platform_admin).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import AnalyticsDbDep, FeedbackDbDep, OrgAdminDep
from repositories.analytics_repo import AnalyticsRepository
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    CommitteePerformanceItem,
    CommitteePerformanceResponse,
    LastLoginsResponse,
    LoginNotReadItem,
    LoginNotReadResponse,
    StaffLoginItem,
    UnreadAssignedItem,
    UnreadAssignedResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/staff", tags=["Analytics — Staff"])


# ── GET /analytics/staff/committee-performance ───────────────────────────────

@router.get("/committee-performance", response_model=CommitteePerformanceResponse)
async def get_committee_performance(
    project_id:  UUID           = Query(...),
    date_from:   Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    use_live:    bool            = Query(False, description="Force live query from feedback_db"),
    _token: OrgAdminDep = None,
    an_db:  AnalyticsDbDep = None,
    fb_db:  FeedbackDbDep = None,
) -> CommitteePerformanceResponse:
    """
    Performance metrics per committee: cases assigned, resolved, overdue,
    avg resolution hours, and resolution rate.
    Uses pre-computed analytics_db data unless use_live=true.
    """
    from datetime import date as _date

    if not use_live:
        # Try pre-computed data from analytics_db
        an_repo = AnalyticsRepository(an_db)
        d_from = _date.fromisoformat(date_from) if date_from else None
        d_to   = _date.fromisoformat(date_to)   if date_to   else None
        records = await an_repo.get_committee_performance_precomputed(project_id, d_from, d_to)

        if records:
            items = [
                CommitteePerformanceItem(
                    committee_id         = rec.committee_id,
                    project_id           = rec.project_id,
                    cases_assigned       = rec.cases_assigned,
                    cases_resolved       = rec.cases_resolved,
                    cases_overdue        = rec.cases_overdue,
                    avg_resolution_hours = rec.avg_resolution_hours,
                    resolution_rate      = rec.resolution_rate,
                )
                for rec in records
            ]
            return CommitteePerformanceResponse(total=len(items), items=items)

    # Fallback: live query from feedback_db
    fb_repo = FeedbackAnalyticsRepository(fb_db)
    rows = await fb_repo.get_committee_performance(project_id)

    items = [
        CommitteePerformanceItem(
            committee_id         = r["committee_id"],
            committee_name       = r.get("committee_name"),
            level                = r.get("level"),
            project_id           = r.get("project_id"),
            cases_assigned       = int(r.get("cases_assigned", 0)),
            cases_resolved       = int(r.get("cases_resolved", 0)),
            cases_overdue        = int(r.get("cases_overdue", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
            resolution_rate      = float(r["resolution_rate"]) if r.get("resolution_rate") is not None else None,
        )
        for r in rows
    ]
    return CommitteePerformanceResponse(total=len(items), items=items)


# ── GET /analytics/staff/last-logins ─────────────────────────────────────────

@router.get("/last-logins", response_model=LastLoginsResponse)
async def get_staff_last_logins(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: OrgAdminDep = None,
    an_db:  AnalyticsDbDep = None,
) -> LastLoginsResponse:
    """
    Last login time and 7-day login count for each staff member.
    Data sourced from analytics_db.staff_logins.
    """
    from datetime import date as _date

    an_repo = AnalyticsRepository(an_db)
    dt_from = None
    dt_to   = None

    if date_from:
        d = _date.fromisoformat(date_from)
        dt_from = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    if date_to:
        d = _date.fromisoformat(date_to)
        dt_to = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)

    rows = await an_repo.get_last_login_per_user(date_from=dt_from, date_to=dt_to)

    items = [
        StaffLoginItem(
            user_id        = r["user_id"],
            last_login_at  = r.get("last_login_at"),
            login_count_7d = int(r.get("login_count_7d", 0)),
            platform       = r.get("platform"),
        )
        for r in rows
    ]
    return LastLoginsResponse(total=len(items), items=items)


# ── GET /analytics/staff/unread-assigned ─────────────────────────────────────

@router.get("/unread-assigned", response_model=UnreadAssignedResponse)
async def get_staff_unread_assigned(
    project_id: UUID = Query(...),
    _token: OrgAdminDep = None,
    fb_db:  FeedbackDbDep = None,
) -> UnreadAssignedResponse:
    """
    Officers who have feedbacks assigned but have not yet taken any action.
    Returns per-officer counts and feedback IDs.
    """
    fb_repo = FeedbackAnalyticsRepository(fb_db)

    # Get unread (no action taken) per officer
    unread_rows = await fb_repo.get_staff_unread_assigned(project_id)
    unread_map = {
        r["user_id"]: {
            "unread_count": int(r.get("unread_count", 0)),
            "feedback_ids": list(r.get("feedback_ids") or []),
        }
        for r in unread_rows
    }

    # Get total assigned per officer for context
    assigned_rows = await fb_repo.get_all_assigned_per_officer(project_id)
    assigned_map = {
        r["user_id"]: int(r.get("assigned_count", 0))
        for r in assigned_rows
    }

    items = [
        UnreadAssignedItem(
            user_id       = uid,
            assigned_count= assigned_map.get(uid, data["unread_count"]),
            unread_count  = data["unread_count"],
            feedback_ids  = data["feedback_ids"],
        )
        for uid, data in unread_map.items()
    ]
    items.sort(key=lambda x: x.unread_count, reverse=True)

    return UnreadAssignedResponse(total=len(items), items=items)


# ── GET /analytics/staff/login-not-read ──────────────────────────────────────

@router.get("/login-not-read", response_model=LoginNotReadResponse)
async def get_staff_login_not_read(
    project_id: UUID = Query(...),
    _token: OrgAdminDep = None,
    an_db:  AnalyticsDbDep = None,
    fb_db:  FeedbackDbDep = None,
) -> LoginNotReadResponse:
    """
    Officers who logged in today AND still have assigned feedbacks with no action taken.
    Helps identify staff who are active but not processing their queue.
    """
    an_repo = AnalyticsRepository(an_db)
    fb_repo = FeedbackAnalyticsRepository(fb_db)

    # Step 1: who logged in today?
    logged_in_today_ids = await an_repo.get_logins_today_user_ids()
    if not logged_in_today_ids:
        return LoginNotReadResponse(total=0, items=[])

    logged_in_set = {str(uid) for uid in logged_in_today_ids}

    # Step 2: who has unread assigned feedbacks?
    unread_rows = await fb_repo.get_staff_unread_assigned(project_id)

    # Step 3: intersection
    # Get last login for each user
    dt_today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    login_rows = await an_repo.get_last_login_per_user(date_from=dt_today_start)
    login_map = {str(r["user_id"]): r.get("last_login_at") for r in login_rows}

    items = []
    for row in unread_rows:
        uid_str = str(row["user_id"])
        if uid_str in logged_in_set:
            items.append(
                LoginNotReadItem(
                    user_id               = row["user_id"],
                    last_login_at         = login_map.get(uid_str),
                    assigned_unread_count = int(row.get("unread_count", 0)),
                    feedback_ids          = list(row.get("feedback_ids") or []),
                )
            )

    items.sort(key=lambda x: x.assigned_unread_count, reverse=True)
    return LoginNotReadResponse(total=len(items), items=items)
