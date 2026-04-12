"""
api/v1/suggestions.py — Analytics endpoints specific to suggestions.
Covers implementation time, frequency, location distribution, and unread tracking.
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
    ImplementationTimeResponse,
    ImplementedResponse,
    ImplementedSuggestionItem,
    SuggestionFrequencyItem,
    SuggestionFrequencyResponse,
    SuggestionImplTimeItem,
    SuggestionLocationItem,
    SuggestionLocationResponse,
    UnreadSuggestionItem,
    UnreadSuggestionsResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/suggestions", tags=["Analytics — Suggestions"])


# ── GET /analytics/suggestions/implementation-time ───────────────────────────

@router.get("/implementation-time", response_model=ImplementationTimeResponse)
async def get_implementation_time(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> ImplementationTimeResponse:
    """
    Hours from submission to implementation (actioned) for all actioned suggestions.
    Returns avg/min/max/median stats and per-item details.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_suggestion_implementation_time(project_id)

    items = [
        SuggestionImplTimeItem(
            feedback_id        = r["feedback_id"],
            unique_ref         = r.get("unique_ref"),
            submitted_at       = r.get("submitted_at"),
            implemented_at     = r.get("implemented_at"),
            hours_to_implement = float(r["hours_to_implement"]) if r.get("hours_to_implement") is not None else None,
            category           = r.get("category"),
        )
        for r in rows
    ]

    hours = [i.hours_to_implement for i in items if i.hours_to_implement is not None]
    return ImplementationTimeResponse(
        avg_hours    = round(sum(hours) / len(hours), 2) if hours else None,
        min_hours    = round(min(hours), 2)               if hours else None,
        max_hours    = round(max(hours), 2)               if hours else None,
        median_hours = round(statistics.median(hours), 2) if hours else None,
        sample_count = len(hours),
        items        = items,
    )


# ── GET /analytics/suggestions/frequency ─────────────────────────────────────

@router.get("/frequency", response_model=SuggestionFrequencyResponse)
async def get_suggestion_frequency(
    project_id: UUID = Query(...),
    period:     str  = Query("week", description="week | month | year"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> SuggestionFrequencyResponse:
    """
    Suggestion frequency broken down by category and priority for the current period.
    """
    if period not in ("week", "month", "year"):
        period = "week"

    period_days_map = {"week": 7, "month": 30, "year": 365}
    period_days = period_days_map[period]

    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_suggestion_frequency(project_id, period=period)

    total = sum(int(r.get("count", 0)) for r in rows)
    items = [
        SuggestionFrequencyItem(
            category    = r.get("category"),
            priority    = r.get("priority"),
            count       = int(r.get("count", 0)),
            rate_per_day= float(r["rate_per_day"]) if r.get("rate_per_day") is not None else None,
        )
        for r in rows
    ]
    return SuggestionFrequencyResponse(
        period      = period,
        period_days = period_days,
        total       = total,
        items       = items,
    )


# ── GET /analytics/suggestions/by-location ───────────────────────────────────

@router.get("/by-location", response_model=SuggestionLocationResponse)
async def get_suggestions_by_location(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> SuggestionLocationResponse:
    """
    Suggestion counts grouped by region/LGA/ward with implementation rates.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_suggestion_by_location(project_id)

    total = sum(int(r.get("count", 0)) for r in rows)
    items = [
        SuggestionLocationItem(
            region              = r.get("region"),
            lga                 = r.get("lga"),
            ward                = r.get("ward"),
            count               = int(r.get("count", 0)),
            implemented_count   = int(r.get("implemented_count", 0)),
            implementation_rate = float(r["implementation_rate"]) if r.get("implementation_rate") is not None else None,
        )
        for r in rows
    ]
    return SuggestionLocationResponse(total=total, items=items)


# ── GET /analytics/suggestions/unread ────────────────────────────────────────

@router.get("/unread", response_model=UnreadSuggestionsResponse)
async def get_unread_suggestions(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> UnreadSuggestionsResponse:
    """
    Suggestions with status='submitted' (not yet acknowledged/actioned).
    Includes days since submission.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_unread_suggestions(project_id)

    items = [
        UnreadSuggestionItem(
            feedback_id  = r["feedback_id"],
            unique_ref   = r.get("unique_ref"),
            submitted_at = r.get("submitted_at"),
            days_unread  = float(r["days_unread"]) if r.get("days_unread") is not None else None,
            priority     = r.get("priority"),
            category     = r.get("category"),
            issue_lga    = r.get("issue_lga"),
        )
        for r in rows
    ]
    return UnreadSuggestionsResponse(total=len(items), items=items)


# ── GET /analytics/suggestions/implemented-today ─────────────────────────────

@router.get("/implemented-today", response_model=ImplementedResponse)
async def get_implemented_today(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> ImplementedResponse:
    """
    Suggestions that were marked as 'actioned' today.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_suggestions_implemented_today(project_id)

    items = [
        ImplementedSuggestionItem(
            feedback_id        = r["feedback_id"],
            unique_ref         = r.get("unique_ref"),
            category           = r.get("category"),
            submitted_at       = r.get("submitted_at"),
            implemented_at     = r.get("implemented_at"),
            hours_to_implement = float(r["hours_to_implement"]) if r.get("hours_to_implement") is not None else None,
        )
        for r in rows
    ]
    return ImplementedResponse(total=len(items), items=items)


# ── GET /analytics/suggestions/implemented-this-week ─────────────────────────

@router.get("/implemented-this-week", response_model=ImplementedResponse)
async def get_implemented_this_week(
    project_id: UUID = Query(...),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> ImplementedResponse:
    """
    Suggestions that were marked as 'actioned' in the current week.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_suggestions_implemented_this_week(project_id)

    items = [
        ImplementedSuggestionItem(
            feedback_id        = r["feedback_id"],
            unique_ref         = r.get("unique_ref"),
            category           = r.get("category"),
            submitted_at       = r.get("submitted_at"),
            implemented_at     = r.get("implemented_at"),
            hours_to_implement = float(r["hours_to_implement"]) if r.get("hours_to_implement") is not None else None,
        )
        for r in rows
    ]
    return ImplementedResponse(total=len(items), items=items)
