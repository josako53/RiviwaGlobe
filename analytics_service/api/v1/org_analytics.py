"""
api/v1/org_analytics.py
────────────────────────────────────────────────────────────────────────────
Organisation-level analytics — aggregates across ALL projects belonging to
an org.  All endpoints accept org_id as a path parameter.

Endpoints
─────────
General
  GET /analytics/org/{org_id}/summary           — counts by type/status/priority
  GET /analytics/org/{org_id}/by-project        — per-project breakdown
  GET /analytics/org/{org_id}/by-period         — submissions over time
  GET /analytics/org/{org_id}/by-channel        — breakdown by intake channel
  GET /analytics/org/{org_id}/by-department     — breakdown by department_id
  GET /analytics/org/{org_id}/by-service        — breakdown by service_id
  GET /analytics/org/{org_id}/by-product        — breakdown by product_id
  GET /analytics/org/{org_id}/by-category       — breakdown by category_def_id

Grievances
  GET /analytics/org/{org_id}/grievances/summary    — unresolved/escalated/avg
  GET /analytics/org/{org_id}/grievances/by-level   — grouped by GRM level
  GET /analytics/org/{org_id}/grievances/by-location — grouped by LGA/ward
  GET /analytics/org/{org_id}/grievances/sla        — SLA compliance across org

Suggestions
  GET /analytics/org/{org_id}/suggestions/summary   — total/actioned/pending
  GET /analytics/org/{org_id}/suggestions/by-project — impl rate per project

Applause
  GET /analytics/org/{org_id}/applause/summary      — total, top categories
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Path, Query

from core.dependencies import FeedbackDbDep, StaffDep
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    FeedbackBreakdownItem,
    FeedbackBreakdownResponse,
    InquirySummaryResponse,
    OrgAppIauseSummaryResponse,
    OrgByChannelItem,
    OrgByChannelResponse,
    OrgByLocationItem,
    OrgByLocationResponse,
    OrgByPeriodItem,
    OrgByPeriodResponse,
    OrgByProjectItem,
    OrgByProjectResponse,
    OrgDimensionBreakdownItem,
    OrgDimensionBreakdownResponse,
    OrgGrievanceByLevelItem,
    OrgGrievanceByLevelResponse,
    OrgGrievanceSLAResponse,
    OrgGrievanceSummaryResponse,
    OrgSLAByPriority,
    OrgSummaryResponse,
    OrgSuggestionByProjectItem,
    OrgSuggestionByProjectResponse,
    OrgSuggestionSummaryResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/org", tags=["Analytics — Organisation"])


# ════════════════════════════════════════════════════════════════════════════
# GENERAL
# ════════════════════════════════════════════════════════════════════════════

@router.get("/{org_id}/summary", response_model=OrgSummaryResponse)
async def org_summary(
    org_id:   UUID          = Path(..., description="Organisation UUID"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgSummaryResponse:
    """
    High-level counts across all projects in the org:
    totals by feedback_type, by status, by priority, and resolution stats.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_summary(org_id, date_from=d_from, date_to=d_to)
    return OrgSummaryResponse(**data)


@router.get("/{org_id}/by-project", response_model=OrgByProjectResponse)
async def org_by_project(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None, description="grievance | suggestion | applause"),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByProjectResponse:
    """
    Feedback counts per project within the org.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_project(org_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [OrgByProjectItem(**r) for r in rows]
    return OrgByProjectResponse(total_items=len(items), items=items)


@router.get("/{org_id}/by-period", response_model=OrgByPeriodResponse)
async def org_by_period(
    org_id:    UUID         = Path(...),
    granularity: str        = Query("day", description="day | week | month"),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    feedback_type: Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByPeriodResponse:
    """
    Submission volume over time at day/week/month granularity.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_period(org_id, granularity=granularity, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [OrgByPeriodItem(**r) for r in rows]
    return OrgByPeriodResponse(granularity=granularity, total_items=len(items), items=items)


@router.get("/{org_id}/by-channel", response_model=OrgByChannelResponse)
async def org_by_channel(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByChannelResponse:
    """
    Feedback counts grouped by intake channel across the org.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_channel(org_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [OrgByChannelItem(**r) for r in rows]
    return OrgByChannelResponse(total_items=len(items), items=items)


def _dim_items(rows: list, dimension: str) -> list:
    return [
        OrgDimensionBreakdownItem(
            dimension_id         = r.get("dimension_id"),
            total                = int(r.get("total", 0)),
            grievances           = int(r.get("grievances", 0)),
            suggestions          = int(r.get("suggestions", 0)),
            applause             = int(r.get("applause", 0)),
            resolved             = int(r.get("resolved", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
        )
        for r in rows
    ]


@router.get("/{org_id}/by-department", response_model=OrgDimensionBreakdownResponse)
async def org_by_department(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """Feedback counts grouped by department_id across the org."""
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_dimension(org_id, dimension="department_id", feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = _dim_items(rows, "department_id")
    return OrgDimensionBreakdownResponse(dimension="department_id", total_items=len(items), items=items)


@router.get("/{org_id}/by-service", response_model=OrgDimensionBreakdownResponse)
async def org_by_service(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """Feedback counts grouped by service_id across the org."""
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_dimension(org_id, dimension="service_id", feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = _dim_items(rows, "service_id")
    return OrgDimensionBreakdownResponse(dimension="service_id", total_items=len(items), items=items)


@router.get("/{org_id}/by-product", response_model=OrgDimensionBreakdownResponse)
async def org_by_product(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """Feedback counts grouped by product_id across the org."""
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_dimension(org_id, dimension="product_id", feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = _dim_items(rows, "product_id")
    return OrgDimensionBreakdownResponse(dimension="product_id", total_items=len(items), items=items)


@router.get("/{org_id}/by-category", response_model=FeedbackBreakdownResponse)
async def org_by_category(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by dynamic category (category_def_id) across the org.
    Includes name/slug from feedback_category_defs. NULL = 'uncategorised'.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_category(org_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackBreakdownItem(
            category_def_id      = r.get("category_def_id"),
            category_name        = r.get("category_name") or "uncategorised",
            category_slug        = r.get("category_slug"),
            total                = int(r.get("total", 0)),
            grievances           = int(r.get("grievances", 0)),
            suggestions          = int(r.get("suggestions", 0)),
            applause             = int(r.get("applause", 0)),
            resolved             = int(r.get("resolved", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
        )
        for r in rows
    ]
    return FeedbackBreakdownResponse(total_items=len(items), items=items)


# ════════════════════════════════════════════════════════════════════════════
# GRIEVANCES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/{org_id}/grievances/summary", response_model=OrgGrievanceSummaryResponse)
async def org_grievance_summary(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceSummaryResponse:
    """
    Org-wide grievance summary: total, unresolved, escalated, dismissed,
    avg resolution hours, avg days unresolved.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_grievance_summary(org_id, date_from=d_from, date_to=d_to)
    return OrgGrievanceSummaryResponse(**data)


@router.get("/{org_id}/grievances/by-level", response_model=OrgGrievanceByLevelResponse)
async def org_grievance_by_level(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceByLevelResponse:
    """
    Grievance counts grouped by current GRM escalation level across the org.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_grievances_by_level(org_id, date_from=d_from, date_to=d_to)
    items = [OrgGrievanceByLevelItem(**r) for r in rows]
    return OrgGrievanceByLevelResponse(total_items=len(items), items=items)


@router.get("/{org_id}/grievances/by-location", response_model=OrgByLocationResponse)
async def org_grievance_by_location(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgByLocationResponse:
    """
    Grievance counts grouped by LGA and ward across the org.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_location(org_id, feedback_type="GRIEVANCE", date_from=d_from, date_to=d_to)
    items = [OrgByLocationItem(**r) for r in rows]
    return OrgByLocationResponse(total_items=len(items), items=items)


@router.get("/{org_id}/grievances/sla", response_model=OrgGrievanceSLAResponse)
async def org_grievance_sla(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceSLAResponse:
    """
    Org-wide SLA compliance for grievances, grouped by priority.
    SLA targets: critical 4h/72h, high 8h/168h, medium 24h/336h, low 48h/720h
    (ack hours / resolution hours).
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_grievance_sla(org_id, date_from=d_from, date_to=d_to)
    return OrgGrievanceSLAResponse(
        by_priority=[OrgSLAByPriority(**b) for b in data.get("by_priority", [])],
        total_breached=data.get("total_breached", 0),
        overall_compliance_rate=data.get("overall_compliance_rate"),
    )


# ════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/{org_id}/suggestions/summary", response_model=OrgSuggestionSummaryResponse)
async def org_suggestion_summary(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgSuggestionSummaryResponse:
    """
    Org-wide suggestion summary: total, actioned, noted, pending (submitted/acknowledged),
    actioned_rate, avg hours to implement.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_suggestion_summary(org_id, date_from=d_from, date_to=d_to)
    return OrgSuggestionSummaryResponse(**data)


@router.get("/{org_id}/suggestions/by-project", response_model=OrgSuggestionByProjectResponse)
async def org_suggestions_by_project(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgSuggestionByProjectResponse:
    """
    Suggestion counts and implementation rate per project within the org.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_suggestions_by_project(org_id, date_from=d_from, date_to=d_to)
    items = [OrgSuggestionByProjectItem(**r) for r in rows]
    return OrgSuggestionByProjectResponse(total_items=len(items), items=items)


# ════════════════════════════════════════════════════════════════════════════
# APPLAUSE
# ════════════════════════════════════════════════════════════════════════════

@router.get("/{org_id}/applause/summary", response_model=OrgAppIauseSummaryResponse)
async def org_applause_summary(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgAppIauseSummaryResponse:
    """
    Org-wide applause summary: total, top categories, by project,
    and month-on-month trend.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_applause_summary(org_id, date_from=d_from, date_to=d_to)
    return OrgAppIauseSummaryResponse(**data)


# ════════════════════════════════════════════════════════════════════════════
# INQUIRIES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/{org_id}/inquiries/summary", response_model=InquirySummaryResponse)
async def org_inquiry_summary(
    org_id:    UUID          = Path(...),
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquirySummaryResponse:
    """
    Org-wide inquiry summary: total, open, resolved, dismissed,
    avg response hours, avg days open, open counts by priority.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_inquiry_summary(org_id, date_from=d_from, date_to=d_to)
    return InquirySummaryResponse(**data)
