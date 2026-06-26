"""
api/v1/feedback.py — Analytics endpoints for general feedback metrics.
All endpoints require Bearer JWT authentication and a project_id query param.
"""
from __future__ import annotations

import statistics
from datetime import date
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query

from core.dependencies import FeedbackDbDep, StaffDep, assert_project_org_access, assert_org_access, require_feature
from core.exceptions import ValidationError as AppValidationError
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
    FeedbackBreakdownItem,
    FeedbackBreakdownResponse,
    FeedbackByStageItem,
    FeedbackByStageResponse,
    NotProcessedFeedbackResponse,
    OverdueFeedbackItem,
    OverdueFeedbackResponse,
    ProcessedTodayItem,
    ProcessedTodayResponse,
    ResolvedTodayItem,
    ResolvedTodayResponse,
    TimeToOpenItem,
    TimeToOpenResponse,
    UnreadFeedbackItem,
    UnreadFeedbackResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/feedback", tags=["Analytics — Feedback"],
                   dependencies=[Depends(require_feature("advanced_analytics"))])


# ── GET /analytics/feedback/time-to-open ─────────────────────────────────────

@router.get("/time-to-open", response_model=TimeToOpenResponse)
async def get_time_to_open(
    project_id: UUID = Query(..., description="Project UUID"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> TimeToOpenResponse:
    """
    Average/min/max/median hours from submitted_at to first feedback action,
    per feedback item in the project.
    """
    from datetime import date as _date
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))

    d_from = _date.fromisoformat(date_from) if date_from else None
    d_to   = _date.fromisoformat(date_to)   if date_to   else None

    rows = await repo.get_time_to_open(project_id, d_from, d_to)

    items = [
        TimeToOpenItem(
            feedback_id     = r["feedback_id"],
            unique_ref      = r.get("unique_ref"),
            priority        = r.get("priority"),
            submitted_at    = r.get("submitted_at"),
            first_action_at = r.get("first_action_at"),
            hours_to_open   = float(r["hours_to_open"]) if r.get("hours_to_open") is not None else None,
        )
        for r in rows
    ]

    hours = [i.hours_to_open for i in items if i.hours_to_open is not None]
    return TimeToOpenResponse(
        avg_hours    = round(sum(hours) / len(hours), 2) if hours else None,
        min_hours    = round(min(hours), 2)              if hours else None,
        max_hours    = round(max(hours), 2)              if hours else None,
        median_hours = round(statistics.median(hours), 2) if hours else None,
        sample_count = len(hours),
        items        = items,
    )


# ── GET /analytics/feedback/unread ───────────────────────────────────────────

@router.get("/unread", response_model=UnreadFeedbackResponse)
async def get_unread_feedback(
    project_id:      UUID           = Query(...),
    priority:        Optional[str]  = Query(None, description="Filter by priority"),
    feedback_type:   Optional[str]  = Query(None, description="grievance | suggestion | applause"),
    department_id:   Optional[UUID] = Query(None, description="Filter by department UUID"),
    service_id:      Optional[UUID] = Query(None, description="Filter by service UUID"),
    product_id:      Optional[UUID] = Query(None, description="Filter by product UUID"),
    category_def_id: Optional[UUID] = Query(None, description="Filter by dynamic category UUID"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> UnreadFeedbackResponse:
    """
    All feedbacks with status='submitted' (unread/unacknowledged).
    Optionally filter by priority, feedback_type, department_id, service_id, product_id, category_def_id.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    rows = await repo.get_unread_all(
        project_id, priority=priority, feedback_type=feedback_type,
        department_id=department_id, service_id=service_id,
        product_id=product_id, category_def_id=category_def_id,
    )

    items = [
        UnreadFeedbackItem(
            feedback_id     = r["feedback_id"],
            unique_ref      = r.get("unique_ref"),
            feedback_type   = r.get("feedback_type"),
            priority        = r.get("priority"),
            submitted_at    = r.get("submitted_at"),
            days_waiting    = float(r["days_waiting"]) if r.get("days_waiting") is not None else None,
            channel         = r.get("channel"),
            issue_lga       = r.get("issue_lga"),
            submitter_name  = r.get("submitter_name"),
            department_id   = r.get("department_id"),
            service_id      = r.get("service_id"),
            product_id      = r.get("product_id"),
            category_def_id = r.get("category_def_id"),
        )
        for r in rows
    ]
    return UnreadFeedbackResponse(total=len(items), items=items)


# ── GET /analytics/feedback/overdue ──────────────────────────────────────────

@router.get("/overdue", response_model=OverdueFeedbackResponse)
async def get_overdue_feedback(
    project_id:      Optional[UUID] = Query(None, description="Project UUID (mutually exclusive with org_id)"),
    org_id:          Optional[UUID] = Query(None, description="Organisation UUID — aggregates across all org projects"),
    feedback_type:   Optional[str] = Query(None),
    department_id:   Optional[UUID] = Query(None, description="Filter by department UUID"),
    service_id:      Optional[UUID] = Query(None, description="Filter by service UUID"),
    product_id:      Optional[UUID] = Query(None, description="Filter by product UUID"),
    category_def_id: Optional[UUID] = Query(None, description="Filter by dynamic category UUID"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OverdueFeedbackResponse:
    """
    Feedbacks with status IN ('acknowledged','in_review') where
    target_resolution_date < now().
    Provide either project_id (single project) or org_id (all org projects aggregated).
    """
    repo = FeedbackAnalyticsRepository(fb_db)

    if project_id:
        assert_project_org_access(_token, await repo.get_project_org_id(project_id))
        project_ids = [project_id]
    elif org_id:
        assert_org_access(_token, org_id)
        project_ids = await repo.get_project_ids_for_org(org_id)
        if not project_ids:
            return OverdueFeedbackResponse(total=0, items=[])
    else:
        raise AppValidationError(message="Provide either project_id or org_id.")

    all_rows: list = []
    for pid in project_ids:
        rows = await repo.get_overdue(
            pid, feedback_type=feedback_type,
            department_id=department_id, service_id=service_id,
            product_id=product_id, category_def_id=category_def_id,
        )
        all_rows.extend(rows)

    items = [
        OverdueFeedbackItem(
            feedback_id            = r["feedback_id"],
            unique_ref             = r.get("unique_ref"),
            priority               = r.get("priority"),
            status                 = r.get("status"),
            submitted_at           = r.get("submitted_at"),
            target_resolution_date = r.get("target_resolution_date"),
            days_overdue           = float(r["days_overdue"]) if r.get("days_overdue") is not None else None,
            assigned_to_user_id    = r.get("assigned_to_user_id"),
            committee_id           = r.get("committee_id"),
            department_id          = r.get("department_id"),
            service_id             = r.get("service_id"),
            product_id             = r.get("product_id"),
            category_def_id        = r.get("category_def_id"),
        )
        for r in all_rows
    ]
    return OverdueFeedbackResponse(total=len(items), items=items)


# ── GET /analytics/feedback/not-processed ────────────────────────────────────

@router.get("/not-processed", response_model=NotProcessedFeedbackResponse)
async def get_not_processed_feedback(
    project_id:    UUID          = Query(...),
    feedback_type: Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> NotProcessedFeedbackResponse:
    """
    Feedbacks acknowledged/in_review but not yet resolved.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    rows = await repo.get_read_not_processed(project_id, feedback_type=feedback_type)

    items = [
        OverdueFeedbackItem(
            feedback_id            = r["feedback_id"],
            unique_ref             = r.get("unique_ref"),
            priority               = r.get("priority"),
            status                 = r.get("status"),
            submitted_at           = r.get("submitted_at"),
            target_resolution_date = r.get("target_resolution_date"),
            days_overdue           = float(r["days_overdue"]) if r.get("days_overdue") is not None else None,
            assigned_to_user_id    = r.get("assigned_to_user_id"),
            committee_id           = r.get("committee_id"),
        )
        for r in rows
    ]
    return NotProcessedFeedbackResponse(total=len(items), items=items)


# ── GET /analytics/feedback/processed-today ──────────────────────────────────

@router.get("/processed-today", response_model=ProcessedTodayResponse)
async def get_processed_today(
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
    project_id: Optional[UUID] = Query(default=None),
    org_id: Optional[UUID] = Query(default=None),
) -> ProcessedTodayResponse:
    """
    Feedbacks that moved to 'in_review' status today.
    Pass either project_id (project scope) or org_id (org scope).
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    if project_id:
        assert_project_org_access(_token, await repo.get_project_org_id(project_id))
        rows = await repo.get_processed_today(project_id=project_id)
    elif org_id:
        assert_org_access(_token, org_id)
        rows = await repo.get_processed_today(org_id=org_id)
    else:
        rows = []

    items = [
        ProcessedTodayItem(
            feedback_id  = r["feedback_id"],
            unique_ref   = r.get("unique_ref"),
            priority     = r.get("priority"),
            category     = r.get("category"),
            processed_at = r.get("processed_at"),
        )
        for r in rows
    ]
    return ProcessedTodayResponse(total=len(items), items=items)


# ── GET /analytics/feedback/resolved-today ───────────────────────────────────

@router.get("/resolved-today", response_model=ResolvedTodayResponse)
async def get_resolved_today(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> ResolvedTodayResponse:
    """
    Feedbacks that were resolved today, with resolution duration in hours.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    rows = await repo.get_resolved_today(project_id)

    items = [
        ResolvedTodayItem(
            feedback_id      = r["feedback_id"],
            unique_ref       = r.get("unique_ref"),
            feedback_type    = r.get("feedback_type"),
            priority         = r.get("priority"),
            category         = r.get("category"),
            resolved_at      = r.get("resolved_at"),
            resolution_hours = float(r["resolution_hours"]) if r.get("resolution_hours") is not None else None,
        )
        for r in rows
    ]
    return ResolvedTodayResponse(total=len(items), items=items)


# ── GET /analytics/feedback/by-service ───────────────────────────────────────

@router.get("/by-service", response_model=FeedbackBreakdownResponse)
async def get_feedback_by_service(
    project_id:    UUID          = Query(..., description="Project UUID"),
    feedback_type: Optional[str] = Query(None, description="grievance | suggestion | applause"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by service_id.
    Only includes feedback where service_id is set.
    Returns: service_id, total, grievances, suggestions, applause, resolved, avg_resolution_hours.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_breakdown_by_service(project_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackBreakdownItem(
            service_id           = r.get("service_id"),
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


# ── GET /analytics/feedback/by-product ───────────────────────────────────────

@router.get("/by-product", response_model=FeedbackBreakdownResponse)
async def get_feedback_by_product(
    project_id:    UUID          = Query(..., description="Project UUID"),
    feedback_type: Optional[str] = Query(None, description="grievance | suggestion | applause"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by product_id.
    Only includes feedback where product_id is set.
    Returns: product_id, total, grievances, suggestions, applause, resolved, avg_resolution_hours.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_breakdown_by_product(project_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackBreakdownItem(
            product_id           = r.get("product_id"),
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


# ── GET /analytics/feedback/by-category ──────────────────────────────────────

@router.get("/by-category", response_model=FeedbackBreakdownResponse)
async def get_feedback_by_category(
    project_id:    Optional[UUID] = Query(None, description="Project UUID (mutually exclusive with org_id)"),
    org_id:        Optional[UUID] = Query(None, description="Organisation UUID — aggregates across all org projects"),
    feedback_type: Optional[str] = Query(None, description="grievance | suggestion | applause"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by dynamic category (category_def_id).
    Provide either project_id (single project) or org_id (all org projects aggregated).
    """
    repo = FeedbackAnalyticsRepository(fb_db)

    if project_id:
        assert_project_org_access(_token, await repo.get_project_org_id(project_id))
        project_ids = [project_id]
    elif org_id:
        assert_org_access(_token, org_id)
        project_ids = await repo.get_project_ids_for_org(org_id)
        if not project_ids:
            return FeedbackBreakdownResponse(total_items=0, items=[])
    else:
        raise AppValidationError(message="Provide either project_id or org_id.")

    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None

    # Aggregate category counts across all project_ids
    merged: dict = {}
    for pid in project_ids:
        rows = await repo.get_breakdown_by_category_def(pid, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
        for r in rows:
            key = str(r.get("category_def_id") or "uncategorised")
            if key not in merged:
                merged[key] = dict(r)
            else:
                for field in ("total", "grievances", "suggestions", "applause", "resolved"):
                    merged[key][field] = int(merged[key].get(field, 0)) + int(r.get(field, 0))

    items = [
        FeedbackBreakdownItem(
            category_def_id      = v.get("category_def_id"),
            category_name        = v.get("category_name") or "uncategorised",
            category_slug        = v.get("category_slug"),
            total                = int(v.get("total", 0)),
            grievances           = int(v.get("grievances", 0)),
            suggestions          = int(v.get("suggestions", 0)),
            applause             = int(v.get("applause", 0)),
            resolved             = int(v.get("resolved", 0)),
            avg_resolution_hours = float(v["avg_resolution_hours"]) if v.get("avg_resolution_hours") is not None else None,
        )
        for v in merged.values()
    ]
    return FeedbackBreakdownResponse(total_items=len(items), items=items)


# ── GET /analytics/feedback/by-department ────────────────────────────────────

@router.get("/by-department", response_model=FeedbackBreakdownResponse)
async def get_feedback_by_department(
    project_id:    UUID          = Query(..., description="Project UUID"),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by department_id (branch) within a project.
    Returns grievances, suggestions, applause, inquiries, resolved count and
    avg resolution hours per department — enabling cross-department comparison
    for any or all feedback types.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_breakdown_by_department(project_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackBreakdownItem(
            department_id        = r.get("department_id"),
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


# ── GET /analytics/feedback/by-stage ─────────────────────────────────────────

@router.get("/by-stage", response_model=FeedbackByStageResponse)
async def get_feedback_by_stage(
    project_id:    UUID          = Query(..., description="Project UUID"),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackByStageResponse:
    """
    Feedback counts grouped by sub-project stage (stage_id) within a project.
    Returns stage name, order, and per-type counts — enabling comparison across
    project stages for any or all feedback types.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_breakdown_by_stage(project_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackByStageItem(
            stage_id             = r.get("stage_id"),
            stage_name           = r.get("stage_name"),
            stage_order          = r.get("stage_order"),
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
    return FeedbackByStageResponse(total_items=len(items), items=items)


# ── GET /analytics/feedback/by-branch ────────────────────────────────────────

@router.get("/by-branch", response_model=FeedbackBreakdownResponse)
async def get_feedback_by_branch(
    project_id:    UUID          = Query(..., description="Project UUID"),
    feedback_type: Optional[str] = Query(None, description="GRIEVANCE | SUGGESTION | APPLAUSE | INQUIRY — omit for all"),
    date_from:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:       Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> FeedbackBreakdownResponse:
    """
    Feedback counts grouped by branch_id within a project.
    Returns grievances, suggestions, applause, inquiries, resolved count and
    avg resolution hours per branch — enabling cross-branch comparison
    for any or all feedback types.
    Only includes rows where branch_id IS NOT NULL (set at submission).
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    assert_project_org_access(_token, await repo.get_project_org_id(project_id))
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_breakdown_by_branch(project_id, feedback_type=feedback_type, date_from=d_from, date_to=d_to)
    items = [
        FeedbackBreakdownItem(
            branch_id            = r.get("branch_id"),
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
