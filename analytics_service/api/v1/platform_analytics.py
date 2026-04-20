"""
api/v1/platform_analytics.py
────────────────────────────────────────────────────────────────────────────
Platform-level analytics — aggregates across ALL organisations and ALL projects.
Requires Bearer JWT + staff auth. Intended for platform admins.

Endpoints
─────────
General
  GET /analytics/platform/summary          — totals across all orgs
  GET /analytics/platform/by-org          — per-organisation breakdown
  GET /analytics/platform/by-period       — submissions over time (all orgs)
  GET /analytics/platform/by-channel      — intake channel breakdown (all orgs)

Grievances
  GET /analytics/platform/grievances/summary  — grievance totals across platform
  GET /analytics/platform/grievances/sla      — SLA compliance across platform

Suggestions
  GET /analytics/platform/suggestions/summary — suggestion totals across platform

Applause
  GET /analytics/platform/applause/summary    — applause totals across platform
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from core.dependencies import FeedbackDbDep, StaffDep
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    InquirySummaryResponse,
    OrgApplauseByOrgItem,
    OrgApplauseCategoryItem,
    OrgByChannelItem,
    OrgByChannelResponse,
    OrgByPeriodItem,
    OrgByPeriodResponse,
    OrgGrievanceSLAResponse,
    OrgGrievanceSummaryResponse,
    OrgSLAByPriority,
    OrgSuggestionSummaryResponse,
    PlatformApplauseSummaryResponse,
    PlatformByOrgItem,
    PlatformByOrgResponse,
    PlatformSummaryResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/platform", tags=["Analytics — Platform"])


# ════════════════════════════════════════════════════════════════════════════
# GENERAL
# ════════════════════════════════════════════════════════════════════════════

@router.get("/summary", response_model=PlatformSummaryResponse)
async def platform_summary(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> PlatformSummaryResponse:
    """
    Platform-wide high-level counts across ALL organisations and projects.
    Returns totals by feedback_type, status, priority, and resolution stats.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_summary(date_from=d_from, date_to=d_to)
    return PlatformSummaryResponse(**{k: (v or 0) if isinstance(v, (int, float)) else v for k, v in data.items()})


@router.get("/by-org", response_model=PlatformByOrgResponse)
async def platform_by_org(
    feedback_type: Optional[str] = Query(None, description="grievance | suggestion | applause"),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> PlatformByOrgResponse:
    """
    Feedback counts per organisation across the platform.
    Returns organisation_id, total_projects, and per-type breakdown.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_org(feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        PlatformByOrgItem(
            organisation_id      = r["organisation_id"],
            org_name             = r.get("org_name"),
            total_projects       = int(r.get("total_projects", 0)),
            total                = int(r.get("total", 0)),
            grievances           = int(r.get("grievances", 0)),
            suggestions          = int(r.get("suggestions", 0)),
            applause             = int(r.get("applause", 0)),
            inquiries            = int(r.get("inquiries", 0)),
            unresolved           = int(r.get("unresolved", 0)),
            resolved             = int(r.get("resolved", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
        )
        for r in rows
    ]
    return PlatformByOrgResponse(total_items=len(items), items=items)


@router.get("/by-period", response_model=OrgByPeriodResponse)
async def platform_by_period(
    granularity:   str           = Query("day", description="day | week | month"),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByPeriodResponse:
    """
    Submission volume over time across the entire platform (day/week/month granularity).
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_period(granularity=granularity, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [OrgByPeriodItem(**r) for r in rows]
    return OrgByPeriodResponse(granularity=granularity, total_items=len(items), items=items)


@router.get("/by-channel", response_model=OrgByChannelResponse)
async def platform_by_channel(
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByChannelResponse:
    """
    Feedback counts grouped by intake channel across the entire platform.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_channel(feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [OrgByChannelItem(**r) for r in rows]
    return OrgByChannelResponse(total_items=len(items), items=items)


# ════════════════════════════════════════════════════════════════════════════
# GRIEVANCES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/grievances/summary", response_model=OrgGrievanceSummaryResponse)
async def platform_grievance_summary(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceSummaryResponse:
    """
    Platform-wide grievance summary: total, unresolved, escalated, dismissed,
    avg resolution hours, avg days unresolved, unresolved counts by priority.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_grievance_summary(date_from=d_from, date_to=d_to)
    return OrgGrievanceSummaryResponse(**data)


@router.get("/grievances/sla", response_model=OrgGrievanceSLAResponse)
async def platform_grievance_sla(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceSLAResponse:
    """
    Platform-wide SLA compliance for grievances, grouped by priority.
    SLA targets: critical 4h/72h, high 8h/168h, medium 24h/336h, low 48h/720h.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_grievance_sla(date_from=d_from, date_to=d_to)
    return OrgGrievanceSLAResponse(
        by_priority=[OrgSLAByPriority(**b) for b in data.get("by_priority", [])],
        total_breached=data.get("total_breached", 0),
        overall_compliance_rate=data.get("overall_compliance_rate"),
    )


# ════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/suggestions/summary", response_model=OrgSuggestionSummaryResponse)
async def platform_suggestion_summary(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgSuggestionSummaryResponse:
    """
    Platform-wide suggestion summary: total, actioned, noted, pending, dismissed,
    actioned_rate, avg hours to implement.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_suggestion_summary(date_from=d_from, date_to=d_to)
    return OrgSuggestionSummaryResponse(**data)


# ════════════════════════════════════════════════════════════════════════════
# APPLAUSE
# ════════════════════════════════════════════════════════════════════════════

@router.get("/applause/summary", response_model=PlatformApplauseSummaryResponse)
async def platform_applause_summary(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> PlatformApplauseSummaryResponse:
    """
    Platform-wide applause summary: total, month-on-month change, top categories,
    and breakdown by organisation.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_applause_summary(date_from=d_from, date_to=d_to)
    return PlatformApplauseSummaryResponse(
        total_applause  = data.get("total_applause", 0),
        this_month      = data.get("this_month", 0),
        last_month      = data.get("last_month", 0),
        mom_change      = data.get("mom_change"),
        top_categories  = [OrgApplauseCategoryItem(**c) for c in data.get("top_categories", [])],
        by_org          = [OrgApplauseByOrgItem(**o) for o in data.get("by_org", [])],
    )


# ════════════════════════════════════════════════════════════════════════════
# INQUIRIES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/inquiries/summary", response_model=InquirySummaryResponse)
async def platform_inquiry_summary(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquirySummaryResponse:
    """
    Platform-wide inquiry summary: total, open, resolved, dismissed,
    avg response hours, avg days open, open counts by priority.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_platform_inquiry_summary(date_from=d_from, date_to=d_to)
    return InquirySummaryResponse(**data)
