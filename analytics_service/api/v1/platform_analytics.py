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
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import FeedbackDbDep, StaffDep
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository

from schemas.analytics import (
    FeedbackBreakdownItem,
    FeedbackBreakdownResponse,
    GrievanceDashboardOverdueItem,
    GrievanceDeptBreakdownItem,
    GrievanceListItem,
    GrievanceOrgBreakdownItem,
    GrievancePriorityBreakdownItem,
    GrievanceSummaryStats,
    InquirySummaryResponse,
    OrgApplauseByOrgItem,
    OrgApplauseCategoryItem,
    OrgByChannelItem,
    OrgByChannelResponse,
    OrgByPeriodItem,
    OrgByPeriodResponse,
    OrgDimensionBreakdownItem,
    OrgDimensionBreakdownResponse,
    OrgGrievanceSLAResponse,
    OrgGrievanceSummaryResponse,
    OrgSLAByPriority,
    OrgSuggestionSummaryResponse,
    PaginatedGrievancesResponse,
    PlatformApplauseSummaryResponse,
    PlatformByOrgItem,
    PlatformByOrgResponse,
    PlatformGrievanceDashboardResponse,
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
# DIMENSION BREAKDOWNS  (department / service / product / category / stage)
# ════════════════════════════════════════════════════════════════════════════

def _dim_items(rows: list) -> list[OrgDimensionBreakdownItem]:
    return [
        OrgDimensionBreakdownItem(
            dimension_id         = r.get("dimension_id"),
            total                = int(r.get("total", 0)),
            grievances           = int(r.get("grievances", 0)),
            suggestions          = int(r.get("suggestions", 0)),
            applause             = int(r.get("applause", 0)),
            inquiries            = int(r.get("inquiries", 0)),
            resolved             = int(r.get("resolved", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
        )
        for r in rows
    ]


@router.get("/by-branch", response_model=OrgDimensionBreakdownResponse)
async def platform_by_branch(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """
    Feedback counts grouped by branch_id across the entire platform.
    All filters optional — omit all for platform-wide branch comparison.
    Only includes rows where branch_id IS NOT NULL.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_branch(
        org_id=org_id, project_id=project_id,
        feedback_type=feedback_type, date_from=d_from, date_to=d_to,
    )
    return OrgDimensionBreakdownResponse(dimension="branch_id", total_items=len(rows), items=_dim_items(rows))


@router.get("/by-department", response_model=OrgDimensionBreakdownResponse)
async def platform_by_department(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """
    Feedback counts grouped by department_id (branch) across the platform.
    All filters optional — omit all for platform-wide data.
    Returns per-department breakdown for grievances, suggestions, applause,
    inquiries, resolved count and avg resolution hours for comparison.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_dimension(
        "department_id", org_id=org_id, project_id=project_id,
        feedback_type=feedback_type, date_from=d_from, date_to=d_to,
    )
    return OrgDimensionBreakdownResponse(dimension="department_id", total_items=len(rows), items=_dim_items(rows))


@router.get("/by-service", response_model=OrgDimensionBreakdownResponse)
async def platform_by_service(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """
    Feedback counts grouped by service_id across the platform.
    All filters optional. Returns per-service breakdown for all feedback types.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_dimension(
        "service_id", org_id=org_id, project_id=project_id,
        feedback_type=feedback_type, date_from=d_from, date_to=d_to,
    )
    return OrgDimensionBreakdownResponse(dimension="service_id", total_items=len(rows), items=_dim_items(rows))


@router.get("/by-product", response_model=OrgDimensionBreakdownResponse)
async def platform_by_product(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OrgDimensionBreakdownResponse:
    """
    Feedback counts grouped by product_id across the platform.
    All filters optional. Returns per-product breakdown for all feedback types.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_dimension(
        "product_id", org_id=org_id, project_id=project_id,
        feedback_type=feedback_type, date_from=d_from, date_to=d_to,
    )
    return OrgDimensionBreakdownResponse(dimension="product_id", total_items=len(rows), items=_dim_items(rows))


@router.get("/by-category", response_model=FeedbackBreakdownResponse)
async def platform_by_category(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    feedback_type: Optional[str]  = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by dynamic category (category_def_id) across the platform.
    All filters optional. Rows with NULL category_def_id appear as 'uncategorised'.
    Returns category name, slug, and per-type breakdown for comparison.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_platform_by_category(
        org_id=org_id, project_id=project_id,
        feedback_type=feedback_type, date_from=d_from, date_to=d_to,
    )
    items = [
        FeedbackBreakdownItem(
            category_def_id      = r.get("category_def_id"),
            category_name        = r.get("category_name") or "uncategorised",
            category_slug        = r.get("category_slug"),
            total                = int(r.get("total", 0)),
            grievances           = int(r.get("grievances", 0)),
            suggestions          = int(r.get("suggestions", 0)),
            applause             = int(r.get("applause", 0)),
            inquiries            = int(r.get("inquiries", 0)),
            resolved             = int(r.get("resolved", 0)),
            avg_resolution_hours = float(r["avg_resolution_hours"]) if r.get("avg_resolution_hours") is not None else None,
        )
        for r in rows
    ]
    return FeedbackBreakdownResponse(total_items=len(items), items=items)


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


@router.get("/grievances/dashboard", response_model=PlatformGrievanceDashboardResponse)
async def platform_grievance_dashboard(
    org_id:        Optional[UUID] = Query(None, description="Filter to a specific organisation (omit for all orgs)"),
    project_id:    Optional[UUID] = Query(None, description="Filter to a specific project"),
    department_id: Optional[UUID] = Query(None, description="Filter by department UUID"),
    status:        Optional[str]  = Query(None, description="Filter by status (SUBMITTED, ACKNOWLEDGED, IN_REVIEW, ESCALATED, RESOLVED, CLOSED, DISMISSED)"),
    priority:      Optional[str]  = Query(None, description="Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    page:          int            = Query(1,   ge=1),
    page_size:     int            = Query(50,  ge=1, le=200),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> PlatformGrievanceDashboardResponse:
    """
    Comprehensive grievance dashboard across the entire platform.
    Returns summary stats (totals, resolved on time %, resolved late %, acknowledged %),
    priority breakdown, department breakdown, per-org breakdown, overdue list,
    and paginated full grievance list.
    All filters are optional — omit all to see platform-wide data.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None

    summary_row   = await repo.get_platform_grievance_dashboard_summary(
        org_id=org_id, project_id=project_id, department_id=department_id,
        status=status, priority=priority, date_from=d_from, date_to=d_to,
    )
    priority_rows = await repo.get_platform_grievance_by_priority(
        org_id=org_id, project_id=project_id, department_id=department_id,
        status=status, date_from=d_from, date_to=d_to,
    )
    dept_rows     = await repo.get_platform_grievance_by_dept(
        org_id=org_id, project_id=project_id,
        status=status, priority=priority, date_from=d_from, date_to=d_to,
    )
    org_rows      = await repo.get_platform_grievance_by_org(
        project_id=project_id, department_id=department_id,
        status=status, priority=priority, date_from=d_from, date_to=d_to,
    )
    overdue_rows  = await repo.get_platform_grievance_overdue(
        org_id=org_id, project_id=project_id,
        department_id=department_id, priority=priority,
    )
    list_data     = await repo.get_platform_grievance_list(
        org_id=org_id, project_id=project_id, department_id=department_id,
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

    return PlatformGrievanceDashboardResponse(
        summary      = summary,
        by_priority  = [GrievancePriorityBreakdownItem(**r) for r in priority_rows],
        by_department= [GrievanceDeptBreakdownItem(**r) for r in dept_rows],
        by_org       = [GrievanceOrgBreakdownItem(**r) for r in org_rows],
        overdue      = [GrievanceDashboardOverdueItem(**r) for r in overdue_rows],
        grievances   = PaginatedGrievancesResponse(
            total     = list_data["total"],
            page      = page,
            page_size = page_size,
            items     = [GrievanceListItem(**r) for r in list_data["items"]],
        ),
    )


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
