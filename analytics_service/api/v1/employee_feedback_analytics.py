"""
api/v1/employee_feedback_analytics.py
─────────────────────────────────────────────────────────────────────────────
Analytics for employee internal feedback (staff ratings of their own org)
and a combined consumer + employee performance view.

Endpoints
─────────
  GET /analytics/org/{org_id}/employee-feedback/summary
  GET /analytics/org/{org_id}/employee-feedback/by-category
  GET /analytics/org/{org_id}/employee-feedback/by-department
  GET /analytics/org/{org_id}/employee-feedback/trend
  GET /analytics/org/{org_id}/combined-performance
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Path, Query

from core.dependencies import FeedbackDbDep, StaffDep, assert_org_access
from repositories.employee_feedback_analytics_repo import EmployeeFeedbackAnalyticsRepo

log = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/analytics/org",
    tags=["Analytics — Employee Feedback & Combined Performance"],
)


def _repo(db: FeedbackDbDep) -> EmployeeFeedbackAnalyticsRepo:
    return EmployeeFeedbackAnalyticsRepo(db)


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/employee-feedback/summary",
    summary="Employee feedback summary — totals, applause rate, status breakdown",
)
async def employee_feedback_summary(
    org_id: UUID = Path(...),
    db: FeedbackDbDep = ...,
    token: StaffDep = ...,
    date_from: Optional[date] = Query(default=None, description="YYYY-MM-DD"),
    date_to:   Optional[date] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    assert_org_access(token, org_id)
    data = await _repo(db).get_summary(org_id, date_from, date_to)
    return {
        "org_id":     str(org_id),
        "date_from":  date_from.isoformat() if date_from else None,
        "date_to":    date_to.isoformat() if date_to else None,
        **data,
    }


# ── By category ───────────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/employee-feedback/by-category",
    summary="Employee feedback breakdown by category (working conditions, management, etc.)",
)
async def employee_feedback_by_category(
    org_id: UUID = Path(...),
    db: FeedbackDbDep = ...,
    token: StaffDep = ...,
    date_from: Optional[date] = Query(default=None),
    date_to:   Optional[date] = Query(default=None),
) -> Dict[str, Any]:
    assert_org_access(token, org_id)
    items = await _repo(db).get_by_category(org_id, date_from, date_to)
    return {
        "org_id":     str(org_id),
        "date_from":  date_from.isoformat() if date_from else None,
        "date_to":    date_to.isoformat() if date_to else None,
        "items":      items,
    }


# ── By department ────────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/employee-feedback/by-department",
    summary="Employee feedback breakdown by department and branch",
)
async def employee_feedback_by_department(
    org_id: UUID = Path(...),
    db: FeedbackDbDep = ...,
    token: StaffDep = ...,
    date_from: Optional[date] = Query(default=None),
    date_to:   Optional[date] = Query(default=None),
) -> Dict[str, Any]:
    assert_org_access(token, org_id)
    items = await _repo(db).get_by_department(org_id, date_from, date_to)
    return {
        "org_id":     str(org_id),
        "date_from":  date_from.isoformat() if date_from else None,
        "date_to":    date_to.isoformat() if date_to else None,
        "items":      items,
    }


# ── Trend ─────────────────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/employee-feedback/trend",
    summary="Employee feedback time series (hour / day / week / month)",
)
async def employee_feedback_trend(
    org_id: UUID = Path(...),
    db: FeedbackDbDep = ...,
    token: StaffDep = ...,
    granularity: str  = Query(default="day", description="hour | day | week | month"),
    date_from: Optional[date] = Query(default=None),
    date_to:   Optional[date] = Query(default=None),
) -> Dict[str, Any]:
    assert_org_access(token, org_id)
    items = await _repo(db).get_trend(org_id, granularity, date_from, date_to)
    return {
        "org_id":      str(org_id),
        "granularity": granularity,
        "date_from":   date_from.isoformat() if date_from else None,
        "date_to":     date_to.isoformat() if date_to else None,
        "items":       items,
    }


# ── Combined performance (consumer + employee) ────────────────────────────────

@router.get(
    "/{org_id}/combined-performance",
    summary="Combined org performance — consumer feedback + employee internal feedback",
    description="""
Returns a unified view of organisational health drawing from two feedback sources:

**Consumer feedback** (`feedbacks` table) — grievances, suggestions, applause and
inquiries submitted by members of the public about the organisation's services,
projects, and products.

**Employee feedback** (`employee_feedbacks` table) — internal feedback submitted
by the organisation's own staff about working conditions, management, culture,
compensation, and other internal topics.

**Combined health score:**
- `excellent`          — combined applause rate ≥ 70 %
- `good`               — 50 % – 69 %
- `fair`               — 30 % – 49 %
- `needs_improvement`  — < 30 %
""",
)
async def combined_performance(
    org_id: UUID = Path(...),
    db: FeedbackDbDep = ...,
    token: StaffDep = ...,
    date_from: Optional[date] = Query(default=None, description="YYYY-MM-DD"),
    date_to:   Optional[date] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    assert_org_access(token, org_id)
    return await _repo(db).get_combined_performance(org_id, date_from, date_to)
