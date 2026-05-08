"""
api/v1/branch_analytics.py
────────────────────────────────────────────────────────────────────────────
Comprehensive branch-level analytics for an organisation.

  GET /analytics/org/{org_id}/branches/summary     — all branches at a glance
  GET /analytics/org/{org_id}/branches/performance — ranking by resolution rate
  GET /analytics/org/{org_id}/branches/trend       — multi-branch time series
  GET /analytics/org/{org_id}/branches/{branch_id}/detail — single-branch deep-dive
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import FeedbackDbDep, OrgAdminDep, assert_org_access
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.branch_analytics import (
    BranchCategoryItem,
    BranchDayItem,
    BranchDeptItem,
    BranchDetailResponse,
    BranchPerformanceItem,
    BranchPerformanceResponse,
    BranchServiceItem,
    BranchSummaryItem,
    BranchSummaryResponse,
    BranchTrendItem,
    BranchTrendResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/org", tags=["Analytics — Branch"])


# ── GET /analytics/org/{org_id}/branches/summary ─────────────────────────────

@router.get("/{org_id}/branches/summary", response_model=BranchSummaryResponse)
async def get_branches_summary(
    org_id:        UUID,
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY"),
    date_from:     Optional[date] = Query(None, description="YYYY-MM-DD"),
    date_to:       Optional[date] = Query(None, description="YYYY-MM-DD"),
    token: OrgAdminDep  = None,
    fb_db: FeedbackDbDep = None,
) -> BranchSummaryResponse:
    """
    Summary for every branch in the organisation: total feedback, counts by type,
    open/resolved/escalated/overdue counts, avg resolution hours, resolution rate,
    and escalation rate — all in a single response ordered by total DESC.
    """
    assert_org_access(token, org_id)
    repo  = FeedbackAnalyticsRepository(fb_db)
    rows  = await repo.get_branches_summary(org_id, date_from, date_to, feedback_type)
    items = [
        BranchSummaryItem(
            branch_id            = r["branch_id"],
            total                = int(r.get("total") or 0),
            grievances           = int(r.get("grievances") or 0),
            suggestions          = int(r.get("suggestions") or 0),
            applause             = int(r.get("applause") or 0),
            inquiries            = int(r.get("inquiries") or 0),
            resolved             = int(r.get("resolved") or 0),
            open_count           = int(r.get("open_count") or 0),
            escalated            = int(r.get("escalated") or 0),
            dismissed            = int(r.get("dismissed") or 0),
            overdue              = int(r.get("overdue") or 0),
            avg_resolution_hours = _f(r.get("avg_resolution_hours")),
            resolution_rate      = _f(r.get("resolution_rate")),
            escalation_rate      = _f(r.get("escalation_rate")),
        )
        for r in rows
    ]
    return BranchSummaryResponse(
        org_id=org_id,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        feedback_type=feedback_type,
        total_branches=len(items),
        items=items,
    )


# ── GET /analytics/org/{org_id}/branches/performance ─────────────────────────

@router.get("/{org_id}/branches/performance", response_model=BranchPerformanceResponse)
async def get_branches_performance(
    org_id:        UUID,
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY"),
    date_from:     Optional[date] = Query(None, description="YYYY-MM-DD"),
    date_to:       Optional[date] = Query(None, description="YYYY-MM-DD"),
    token: OrgAdminDep  = None,
    fb_db: FeedbackDbDep = None,
) -> BranchPerformanceResponse:
    """
    Branch performance league table, ranked best-to-worst by resolution rate.
    Branches with identical rates are sorted by lowest overdue count, then total volume.

    Use this to identify which branches need operational support, training, or
    additional staffing to improve their complaint resolution rates.
    """
    assert_org_access(token, org_id)
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_branches_summary(org_id, date_from, date_to, feedback_type)

    def _rank_key(r: dict) -> tuple:
        rate    = float(r.get("resolution_rate") or 0)
        overdue = int(r.get("overdue") or 0)
        total   = int(r.get("total") or 0)
        return (-rate, overdue, -total)   # best rate first; fewest overdue; most volume

    ranked = sorted(rows, key=_rank_key)
    items  = [
        BranchPerformanceItem(
            rank                 = idx + 1,
            branch_id            = r["branch_id"],
            total                = int(r.get("total") or 0),
            grievances           = int(r.get("grievances") or 0),
            suggestions          = int(r.get("suggestions") or 0),
            applause             = int(r.get("applause") or 0),
            inquiries            = int(r.get("inquiries") or 0),
            resolved             = int(r.get("resolved") or 0),
            open_count           = int(r.get("open_count") or 0),
            escalated            = int(r.get("escalated") or 0),
            overdue              = int(r.get("overdue") or 0),
            avg_resolution_hours = _f(r.get("avg_resolution_hours")),
            resolution_rate      = _f(r.get("resolution_rate")),
            escalation_rate      = _f(r.get("escalation_rate")),
        )
        for idx, r in enumerate(ranked)
    ]
    return BranchPerformanceResponse(
        org_id=org_id,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        total_branches=len(items),
        items=items,
    )


# ── GET /analytics/org/{org_id}/branches/trend ───────────────────────────────

@router.get("/{org_id}/branches/trend", response_model=BranchTrendResponse)
async def get_branches_trend(
    org_id:        UUID,
    granularity:   str           = Query("day",  description="hour | day | week | month"),
    feedback_type: Optional[str] = Query(None,   description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY"),
    date_from:     Optional[date]= Query(None,   description="YYYY-MM-DD"),
    date_to:       Optional[date]= Query(None,   description="YYYY-MM-DD"),
    token: OrgAdminDep  = None,
    fb_db: FeedbackDbDep = None,
) -> BranchTrendResponse:
    """
    Multi-branch feedback time series — each row is one (branch_id, period) pair.

    Useful for overlaying multiple branches on a comparison chart to spot which
    branches have surging complaint volumes or declining resolution counts.
    Use granularity=week or month for longer-range trend analysis.
    """
    assert_org_access(token, org_id)
    if granularity not in ("hour", "day", "week", "month"):
        granularity = "day"
    repo  = FeedbackAnalyticsRepository(fb_db)
    rows  = await repo.get_branches_trend(org_id, date_from, date_to, granularity, feedback_type)
    items = [
        BranchTrendItem(
            branch_id   = r["branch_id"],
            period      = r.get("period"),
            total       = int(r.get("total") or 0),
            grievances  = int(r.get("grievances") or 0),
            suggestions = int(r.get("suggestions") or 0),
            applause    = int(r.get("applause") or 0),
            inquiries   = int(r.get("inquiries") or 0),
            resolved    = int(r.get("resolved") or 0),
        )
        for r in rows
    ]
    return BranchTrendResponse(
        org_id=org_id,
        granularity=granularity,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        items=items,
    )


# ── GET /analytics/org/{org_id}/branches/{branch_id}/detail ──────────────────

@router.get("/{org_id}/branches/{branch_id}/detail", response_model=BranchDetailResponse)
async def get_branch_detail(
    org_id:    UUID,
    branch_id: UUID,
    date_from: Optional[date] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[date] = Query(None, description="YYYY-MM-DD"),
    token: OrgAdminDep  = None,
    fb_db: FeedbackDbDep = None,
) -> BranchDetailResponse:
    """
    Complete analytics for a single branch:

    - Summary totals with resolution rate, escalation rate, overdue + critical/high open counts
    - Breakdown by department within the branch
    - Top 15 categories driving feedback at this branch
    - Top 10 services with most feedback
    - Daily trend for the selected date range

    The combination of resolution_rate + overdue + critical_open gives a complete
    operational health picture of one branch.
    """
    assert_org_access(token, org_id)
    repo   = FeedbackAnalyticsRepository(fb_db)
    detail = await repo.get_branch_detail(org_id, branch_id, date_from, date_to)

    by_dept = [
        BranchDeptItem(
            department_id        = r.get("department_id"),
            total                = int(r.get("total") or 0),
            grievances           = int(r.get("grievances") or 0),
            applause             = int(r.get("applause") or 0),
            resolved             = int(r.get("resolved") or 0),
            avg_resolution_hours = _f(r.get("avg_resolution_hours")),
        )
        for r in detail.get("by_department", [])
    ]
    by_cat = [
        BranchCategoryItem(
            category_def_id = r.get("category_def_id"),
            category        = r.get("category"),
            total           = int(r.get("total") or 0),
            grievances      = int(r.get("grievances") or 0),
            resolved        = int(r.get("resolved") or 0),
        )
        for r in detail.get("by_category", [])
    ]
    by_svc = [
        BranchServiceItem(
            service_id = r.get("service_id"),
            total      = int(r.get("total") or 0),
            grievances = int(r.get("grievances") or 0),
            resolved   = int(r.get("resolved") or 0),
        )
        for r in detail.get("by_service", [])
    ]
    trend = [
        BranchDayItem(
            period      = r.get("period"),
            total       = int(r.get("total") or 0),
            grievances  = int(r.get("grievances") or 0),
            suggestions = int(r.get("suggestions") or 0),
            applause    = int(r.get("applause") or 0),
            inquiries   = int(r.get("inquiries") or 0),
        )
        for r in detail.get("trend", [])
    ]

    return BranchDetailResponse(
        org_id               = org_id,
        branch_id            = branch_id,
        date_from            = str(date_from) if date_from else None,
        date_to              = str(date_to) if date_to else None,
        total                = int(detail.get("total") or 0),
        grievances           = int(detail.get("grievances") or 0),
        suggestions          = int(detail.get("suggestions") or 0),
        applause             = int(detail.get("applause") or 0),
        inquiries            = int(detail.get("inquiries") or 0),
        resolved             = int(detail.get("resolved") or 0),
        open_count           = int(detail.get("open_count") or 0),
        escalated            = int(detail.get("escalated") or 0),
        dismissed            = int(detail.get("dismissed") or 0),
        overdue              = int(detail.get("overdue") or 0),
        critical_open        = int(detail.get("critical_open") or 0),
        high_open            = int(detail.get("high_open") or 0),
        avg_resolution_hours = _f(detail.get("avg_resolution_hours")),
        resolution_rate      = _f(detail.get("resolution_rate")),
        escalation_rate      = _f(detail.get("escalation_rate")),
        by_department        = by_dept,
        by_category          = by_cat,
        by_service           = by_svc,
        trend                = trend,
    )


# ── helper ────────────────────────────────────────────────────────────────────

def _f(v: object) -> Optional[float]:
    return float(v) if v is not None else None  # type: ignore[arg-type]
