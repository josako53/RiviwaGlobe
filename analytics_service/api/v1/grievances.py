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
    HotspotAlertItem,
    HotspotResponse,
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
