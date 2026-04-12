"""
api/v1/feedback.py — Analytics endpoints for general feedback metrics.
All endpoints require Bearer JWT authentication and a project_id query param.
"""
from __future__ import annotations

import statistics
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Query

from core.dependencies import FeedbackDbDep, StaffDep
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import (
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
router = APIRouter(prefix="/analytics/feedback", tags=["Analytics — Feedback"])


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
    project_id:    UUID           = Query(...),
    priority:      Optional[str]  = Query(None, description="Filter by priority"),
    feedback_type: Optional[str]  = Query(None, description="grievance | suggestion | applause"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> UnreadFeedbackResponse:
    """
    All feedbacks with status='submitted' (unread/unacknowledged).
    Optionally filter by priority and feedback_type.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_unread_all(project_id, priority=priority, feedback_type=feedback_type)

    items = [
        UnreadFeedbackItem(
            feedback_id   = r["feedback_id"],
            unique_ref    = r.get("unique_ref"),
            feedback_type = r.get("feedback_type"),
            priority      = r.get("priority"),
            submitted_at  = r.get("submitted_at"),
            days_waiting  = float(r["days_waiting"]) if r.get("days_waiting") is not None else None,
            channel       = r.get("channel"),
            issue_lga     = r.get("issue_lga"),
            submitter_name= r.get("submitter_name"),
        )
        for r in rows
    ]
    return UnreadFeedbackResponse(total=len(items), items=items)


# ── GET /analytics/feedback/overdue ──────────────────────────────────────────

@router.get("/overdue", response_model=OverdueFeedbackResponse)
async def get_overdue_feedback(
    project_id:    UUID          = Query(...),
    feedback_type: Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> OverdueFeedbackResponse:
    """
    Feedbacks with status IN ('acknowledged','in_review') where
    target_resolution_date < now().
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_overdue(project_id, feedback_type=feedback_type)

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
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> ProcessedTodayResponse:
    """
    Feedbacks that moved to 'in_review' status today.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_processed_today(project_id)

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
