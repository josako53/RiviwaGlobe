"""
api/v1/grievances.py — Analytics endpoints specific to grievances.
Includes unresolved grievances, SLA compliance, and hotspot detection.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import AnalyticsDbDep, FeedbackDbDep, StaffDep
from repositories.analytics_repo import AnalyticsRepository
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    GrievanceDashboardOverdueItem,
    GrievanceDashboardResponse,
    GrievanceDeptBreakdownItem,
    GrievanceListItem,
    GrievancePriorityBreakdownItem,
    GrievanceStageBreakdownItem,
    GrievanceSummaryStats,
    HotspotAlertItem,
    HotspotResponse,
    PaginatedGrievancesResponse,
    SLAByPriority,
    SLAOverdueItem,
    SLAStatusResponse,
    UnresolvedGrievanceItem,
    UnresolvedGrievancesResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/grievances", tags=["Analytics — Grievances"])

# SLA targets (hours)
_ACK_HOURS  = {"critical": 4,   "high": 8,   "medium": 24,  "low": 48}
_RES_HOURS  = {"critical": 72,  "high": 168, "medium": 336, "low": 720}


# ── GET /analytics/grievances/unresolved ─────────────────────────────────────

@router.get("/unresolved", response_model=UnresolvedGrievancesResponse)
async def get_unresolved_grievances(
    project_id:      UUID           = Query(...),
    min_days:        Optional[float] = Query(None, description="Minimum days unresolved"),
    priority:        Optional[str]  = Query(None),
    status:          Optional[str]  = Query(None, description="Specific status to filter by"),
    department_id:   Optional[UUID] = Query(None, description="Filter by department UUID"),
    service_id:      Optional[UUID] = Query(None, description="Filter by service UUID"),
    product_id:      Optional[UUID] = Query(None, description="Filter by product UUID"),
    category_def_id: Optional[UUID] = Query(None, description="Filter by dynamic category UUID"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> UnresolvedGrievancesResponse:
    """
    All grievances not yet resolved (status NOT IN resolved/closed/dismissed).
    Filterable by min_days, priority, status, department_id, service_id, product_id, category_def_id.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_unresolved_grievances(
        project_id,
        min_days=min_days,
        priority=priority,
        status=status,
        department_id=department_id,
        service_id=service_id,
        product_id=product_id,
        category_def_id=category_def_id,
    )

    items = [
        UnresolvedGrievanceItem(
            feedback_id         = r["feedback_id"],
            unique_ref          = r.get("unique_ref"),
            priority            = r.get("priority"),
            category            = r.get("category"),
            status              = r.get("status"),
            submitted_at        = r.get("submitted_at"),
            days_unresolved     = float(r["days_unresolved"]) if r.get("days_unresolved") is not None else None,
            assigned_to_user_id = r.get("assigned_to_user_id"),
            committee_id        = r.get("committee_id"),
            issue_lga           = r.get("issue_lga"),
            issue_ward          = r.get("issue_ward"),
            department_id       = r.get("department_id"),
            service_id          = r.get("service_id"),
            product_id          = r.get("product_id"),
            category_def_id     = r.get("category_def_id"),
        )
        for r in rows
    ]
    return UnresolvedGrievancesResponse(total=len(items), items=items)


# ── GET /analytics/grievances/sla-status ─────────────────────────────────────

@router.get("/sla-status", response_model=SLAStatusResponse)
async def get_sla_status(
    project_id:    UUID = Query(...),
    breached_only: bool = Query(False, description="Return only breached records"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
    an_db:  AnalyticsDbDep = None,
) -> SLAStatusResponse:
    """
    SLA compliance status for grievances in the project.
    Returns per-priority breakdown (ack SLA met/breached, resolution SLA met/breached)
    and a flat overdue list. Uses pre-computed analytics_db data when available,
    falling back to live feedback_db query.
    """
    # Try pre-computed analytics_db first
    an_repo = AnalyticsRepository(an_db)
    sla_records = await an_repo.get_sla_status(project_id, breached_only=breached_only)

    if sla_records:
        # Build response from pre-computed records
        priority_buckets: dict[str, dict] = {}
        overdue_items = []
        total_breached = 0

        for rec in sla_records:
            p = rec.priority or "unknown"
            if p not in priority_buckets:
                priority_buckets[p] = {
                    "priority": p,
                    "total": 0,
                    "ack_met": 0,
                    "ack_breached": 0,
                    "res_met": 0,
                    "res_breached": 0,
                }
            b = priority_buckets[p]
            b["total"] += 1
            if rec.ack_sla_met is True:
                b["ack_met"] += 1
            if rec.ack_sla_breached:
                b["ack_breached"] += 1
            if rec.res_sla_met is True:
                b["res_met"] += 1
            if rec.res_sla_breached:
                b["res_breached"] += 1
                total_breached += 1

            if rec.ack_sla_breached or rec.res_sla_breached:
                overdue_items.append(
                    SLAOverdueItem(
                        feedback_id     = rec.feedback_id,
                        priority        = rec.priority,
                        submitted_at    = rec.submitted_at,
                        ack_deadline    = rec.ack_deadline,
                        res_deadline    = rec.res_deadline,
                        acknowledged_at = rec.acknowledged_at,
                        resolved_at     = rec.resolved_at,
                        ack_sla_met     = rec.ack_sla_met,
                        res_sla_met     = rec.res_sla_met,
                        days_unresolved = rec.days_unresolved,
                    )
                )

        by_priority = []
        total_all = sum(b["total"] for b in priority_buckets.values())
        total_met  = sum(b["res_met"] for b in priority_buckets.values())
        for b in priority_buckets.values():
            t = b["total"]
            compliance = round((b["res_met"] / t) * 100, 2) if t > 0 else None
            by_priority.append(SLAByPriority(compliance_rate=compliance, **b))

        overall = round((total_met / total_all) * 100, 2) if total_all > 0 else None
        return SLAStatusResponse(
            by_priority             = by_priority,
            overdue_list            = overdue_items,
            total_breached          = total_breached,
            overall_compliance_rate = overall,
        )

    # Fallback: compute live from feedback_db
    fb_repo = FeedbackAnalyticsRepository(fb_db)
    unresolved_rows = await fb_repo.get_unresolved_grievances(project_id)

    from datetime import timedelta, datetime, timezone as _tz
    priority_buckets: dict[str, dict] = {}
    overdue_items = []
    total_breached = 0

    for r in unresolved_rows:
        p = (r.get("priority") or "low").lower()
        submitted_at = r.get("submitted_at")
        if p not in priority_buckets:
            priority_buckets[p] = {
                "priority": p, "total": 0, "ack_met": 0,
                "ack_breached": 0, "res_met": 0, "res_breached": 0,
            }
        b = priority_buckets[p]
        b["total"] += 1

        if submitted_at:
            now = datetime.now(_tz.utc)
            ack_hours = _ACK_HOURS.get(p, 48)
            res_hours = _RES_HOURS.get(p, 720)
            ack_deadline = submitted_at + timedelta(hours=ack_hours)
            res_deadline = submitted_at + timedelta(hours=res_hours)
            res_breached = res_deadline < now
            if res_breached:
                b["res_breached"] += 1
                total_breached += 1
                days_unresolved = float(r.get("days_unresolved") or 0)
                overdue_items.append(
                    SLAOverdueItem(
                        feedback_id     = r["feedback_id"],
                        priority        = p,
                        submitted_at    = submitted_at,
                        ack_deadline    = ack_deadline,
                        res_deadline    = res_deadline,
                        days_unresolved = days_unresolved,
                    )
                )

    by_priority = []
    total_all = sum(b["total"] for b in priority_buckets.values())
    total_met  = sum(b["res_met"] for b in priority_buckets.values())
    for b in priority_buckets.values():
        t = b["total"]
        compliance = round((b["res_met"] / t) * 100, 2) if t > 0 else None
        by_priority.append(SLAByPriority(compliance_rate=compliance, **b))

    overall = round((total_met / total_all) * 100, 2) if total_all > 0 else None
    return SLAStatusResponse(
        by_priority             = by_priority,
        overdue_list            = overdue_items,
        total_breached          = total_breached,
        overall_compliance_rate = overall,
    )


# ── GET /analytics/grievances/dashboard ─────────────────────────────────────

@router.get("/dashboard", response_model=GrievanceDashboardResponse)
async def get_grievance_dashboard(
    project_id:    UUID           = Query(..., description="Project UUID"),
    department_id: Optional[UUID] = Query(None, description="Filter by department UUID"),
    status:        Optional[str]  = Query(None, description="Filter by status (e.g. SUBMITTED, ACKNOWLEDGED, IN_REVIEW, ESCALATED, RESOLVED, CLOSED, DISMISSED)"),
    priority:      Optional[str]  = Query(None, description="Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)"),
    date_from:     Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str]  = Query(None, description="ISO date YYYY-MM-DD"),
    page:          int            = Query(1,   ge=1),
    page_size:     int            = Query(50,  ge=1, le=200),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> GrievanceDashboardResponse:
    """
    Comprehensive grievance dashboard for a project.
    Returns:
    - summary stats (totals, resolved on time %, resolved late %, acknowledged %)
    - breakdown by priority (CRITICAL/HIGH/MEDIUM/LOW)
    - breakdown by department
    - breakdown by project stage (sub-project equivalent)
    - overdue grievances list (top 100)
    - paginated full grievance list
    Filterable by department_id, status, priority, date_from, date_to.
    """
    from datetime import date as _date
    d_from = _date.fromisoformat(date_from) if date_from else None
    d_to   = _date.fromisoformat(date_to)   if date_to   else None

    repo = FeedbackAnalyticsRepository(fb_db)

    summary_row, priority_rows, dept_rows, stage_rows, overdue_rows, list_data = (
        await repo.get_project_grievance_dashboard_summary(
            project_id, department_id=department_id, status=status,
            priority=priority, date_from=d_from, date_to=d_to,
        ),
        await repo.get_project_grievance_by_priority(
            project_id, department_id=department_id, status=status,
            date_from=d_from, date_to=d_to,
        ),
        await repo.get_project_grievance_by_dept(
            project_id, status=status, priority=priority,
            date_from=d_from, date_to=d_to,
        ),
        await repo.get_project_grievance_by_stage(
            project_id, status=status, priority=priority,
            date_from=d_from, date_to=d_to,
        ),
        await repo.get_project_grievance_overdue(
            project_id, department_id=department_id, priority=priority,
        ),
        await repo.get_project_grievance_list(
            project_id, department_id=department_id, status=status,
            priority=priority, date_from=d_from, date_to=d_to,
            page=page, page_size=page_size,
        ),
    )

    total = int(summary_row.get("total_grievances") or 0)
    resolved = int(summary_row.get("resolved") or 0)
    closed = int(summary_row.get("closed") or 0)
    resolved_total = resolved + closed
    ack_count = int(summary_row.get("acknowledged_count") or 0)
    res_on_time = int(summary_row.get("resolved_on_time") or 0)
    res_late = int(summary_row.get("resolved_late") or 0)
    res_with_deadline = res_on_time + res_late

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
        resolved_on_time_pct = round(res_on_time / res_with_deadline * 100, 2) if res_with_deadline > 0 else None,
        resolved_late_pct    = round(res_late / res_with_deadline * 100, 2) if res_with_deadline > 0 else None,
        avg_resolution_hours = summary_row.get("avg_resolution_hours"),
        avg_days_unresolved  = summary_row.get("avg_days_unresolved"),
    )

    return GrievanceDashboardResponse(
        summary      = summary,
        by_priority  = [GrievancePriorityBreakdownItem(**r) for r in priority_rows],
        by_department= [GrievanceDeptBreakdownItem(**r) for r in dept_rows],
        by_stage     = [GrievanceStageBreakdownItem(**r) for r in stage_rows],
        overdue      = [GrievanceDashboardOverdueItem(**r) for r in overdue_rows],
        grievances   = PaginatedGrievancesResponse(
            total     = list_data["total"],
            page      = page,
            page_size = page_size,
            items     = [GrievanceListItem(**r) for r in list_data["items"]],
        ),
    )


# ── GET /analytics/grievances/hotspots ───────────────────────────────────────

@router.get("/hotspots", response_model=HotspotResponse)
async def get_hotspots(
    project_id:   UUID = Query(...),
    alert_status: str  = Query("active", description="active | resolved | all"),
    _token: StaffDep = None,
    an_db:  AnalyticsDbDep = None,
) -> HotspotResponse:
    """
    Geographic/category hotspot alerts for the project.
    Returns active spikes where feedback volume significantly exceeds baseline.
    """
    an_repo = AnalyticsRepository(an_db)

    if alert_status == "all":
        # Fetch active first, then resolved
        active   = await an_repo.get_hotspot_alerts(project_id, status="active")
        resolved = await an_repo.get_hotspot_alerts(project_id, status="resolved")
        records  = active + resolved
    else:
        records = await an_repo.get_hotspot_alerts(project_id, status=alert_status)

    alerts = [
        HotspotAlertItem(
            id           = rec.id,
            location     = rec.location,
            category     = rec.category,
            count        = rec.count_in_window,
            spike_factor = rec.spike_factor,
            baseline_avg = rec.baseline_avg,
            window_start = rec.window_start,
            window_end   = rec.window_end,
            alert_status = rec.alert_status,
        )
        for rec in records
    ]
    return HotspotResponse(total=len(alerts), alerts=alerts)
