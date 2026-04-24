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

from core.dependencies import FeedbackDbDep, StaffDep, assert_org_access
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    FeedbackBreakdownItem,
    FeedbackBreakdownResponse,
    GrievanceDashboardOverdueItem,
    GrievanceDeptBreakdownItem,
    GrievanceListItem,
    GrievancePriorityBreakdownItem,
    GrievanceProjectBreakdownItem,
    GrievanceSummaryStats,
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
    OrgGrievanceDashboardResponse,
    OrgGrievanceSLAResponse,
    OrgGrievanceSummaryResponse,
    OrgSLAByPriority,
    OrgSummaryResponse,
    OrgSuggestionByProjectItem,
    OrgSuggestionByProjectResponse,
    OrgSuggestionSummaryResponse,
    PaginatedGrievancesResponse,
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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


@router.get("/{org_id}/by-branch", response_model=OrgDimensionBreakdownResponse)
async def org_by_branch(
    org_id:        UUID          = Path(...),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """
    Feedback counts grouped by branch_id across all projects in the org.
    Returns grievances, suggestions, applause, inquiries, resolved count and
    avg resolution hours per branch — enabling cross-branch comparison.
    Only includes rows where branch_id IS NOT NULL.
    """
    assert_org_access(_token, org_id)
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_branch(org_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = _dim_items(rows, "branch_id")
    return OrgDimensionBreakdownResponse(dimension="branch_id", total_items=len(items), items=items)


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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_org_by_location(org_id, feedback_type="GRIEVANCE", date_from=d_from, date_to=d_to)
    items = [OrgByLocationItem(**r) for r in rows]
    return OrgByLocationResponse(total_items=len(items), items=items)


@router.get("/{org_id}/grievances/dashboard", response_model=OrgGrievanceDashboardResponse)
async def org_grievance_dashboard(
    org_id:        UUID          = Path(..., description="Organisation UUID"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    department_id: Optional[UUID] = Query(None, description="Filter by department UUID"),
    status:        Optional[str]  = Query(None, description="Filter by status"),
    priority:      Optional[str]  = Query(None, description="Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    page:          int            = Query(1,   ge=1),
    page_size:     int            = Query(50,  ge=1, le=200),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgGrievanceDashboardResponse:
    """
    Comprehensive grievance dashboard for an organisation.
    Returns summary stats, priority breakdown, dept breakdown, per-project breakdown,
    overdue list, and paginated grievance list.
    All results scoped to the org; optionally filtered to a single project.
    """
    assert_org_access(_token, org_id)
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None

    summary_row  = await repo.get_org_grievance_dashboard_summary(
        org_id, project_id=project_id, department_id=department_id,
        status=status, priority=priority, date_from=d_from, date_to=d_to,
    )
    priority_rows = await repo.get_org_grievance_by_priority(
        org_id, project_id=project_id, department_id=department_id,
        status=status, date_from=d_from, date_to=d_to,
    )
    dept_rows    = await repo.get_org_grievance_by_dept(
        org_id, project_id=project_id, status=status, priority=priority,
        date_from=d_from, date_to=d_to,
    )
    proj_rows    = await repo.get_org_grievance_by_project(
        org_id, department_id=department_id, status=status, priority=priority,
        date_from=d_from, date_to=d_to,
    )
    overdue_rows = await repo.get_org_grievance_overdue(
        org_id, project_id=project_id, department_id=department_id, priority=priority,
    )
    list_data    = await repo.get_org_grievance_list(
        org_id, project_id=project_id, department_id=department_id,
        status=status, priority=priority, date_from=d_from, date_to=d_to,
        page=page, page_size=page_size,
    )

    total           = int(summary_row.get("total_grievances") or 0)
    resolved        = int(summary_row.get("resolved") or 0)
    closed          = int(summary_row.get("closed") or 0)
    ack_count       = int(summary_row.get("acknowledged_count") or 0)
    res_on_time     = int(summary_row.get("resolved_on_time") or 0)
    res_late        = int(summary_row.get("resolved_late") or 0)
    res_with_dl     = res_on_time + res_late

    summary = GrievanceSummaryStats(
        total_grievances     = total,
        resolved             = resolved,
        closed               = closed,
        unresolved           = int(summary_row.get("unresolved") or 0),
        escalated            = int(summary_row.get("escalated") or 0),
        dismissed            = int(summary_row.get("dismissed") or 0),
        acknowledged_count   = ack_count,
        acknowledged_pct     = round(ack_count / total * 100, 2) if total > 0 else None,
        resolved_on_time     = res_on_time,
        resolved_late        = res_late,
        resolved_on_time_pct = round(res_on_time / res_with_dl * 100, 2) if res_with_dl > 0 else None,
        resolved_late_pct    = round(res_late / res_with_dl * 100, 2) if res_with_dl > 0 else None,
        avg_resolution_hours = summary_row.get("avg_resolution_hours"),
        avg_days_unresolved  = summary_row.get("avg_days_unresolved"),
    )

    return OrgGrievanceDashboardResponse(
        summary      = summary,
        by_priority  = [GrievancePriorityBreakdownItem(**r) for r in priority_rows],
        by_department= [GrievanceDeptBreakdownItem(**r) for r in dept_rows],
        by_project   = [GrievanceProjectBreakdownItem(**r) for r in proj_rows],
        overdue      = [GrievanceDashboardOverdueItem(**r) for r in overdue_rows],
        grievances   = PaginatedGrievancesResponse(
            total     = list_data["total"],
            page      = page,
            page_size = page_size,
            items     = [GrievanceListItem(**r) for r in list_data["items"]],
        ),
    )


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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
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
    assert_org_access(_token, org_id)
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_org_inquiry_summary(org_id, date_from=d_from, date_to=d_to)
    return InquirySummaryResponse(**data)
