"""
api/v1/inquiries.py — Analytics endpoints specific to inquiries.
Covers inquiry summary, unread, overdue, by-channel, by-category.
All endpoints are project-scoped via project_id query param.
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
    InquiryByCategoryItem,
    InquiryByCategoryResponse,
    InquiryByChannelItem,
    InquiryByChannelResponse,
    InquiryOverdueItem,
    InquiryOverdueResponse,
    InquirySummaryResponse,
    InquiryUnreadItem,
    InquiryUnreadResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/inquiries", tags=["Analytics — Inquiries"])


# ── GET /analytics/inquiries/summary ─────────────────────────────────────────

@router.get("/summary", response_model=InquirySummaryResponse)
async def get_inquiry_summary(
    project_id: UUID          = Query(..., description="Project UUID"),
    date_from:  Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:    Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquirySummaryResponse:
    """
    Inquiry summary for a project: total, open, resolved, dismissed,
    avg response hours, avg days open, open counts by priority.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    data = await repo.get_inquiry_summary(project_id, date_from=d_from, date_to=d_to)
    return InquirySummaryResponse(**data)


# ── GET /analytics/inquiries/unread ──────────────────────────────────────────

@router.get("/unread", response_model=InquiryUnreadResponse)
async def get_inquiry_unread(
    project_id:      UUID           = Query(...),
    priority:        Optional[str]  = Query(None, description="Filter by priority"),
    department_id:   Optional[UUID] = Query(None, description="Filter by department UUID"),
    service_id:      Optional[UUID] = Query(None, description="Filter by service UUID"),
    product_id:      Optional[UUID] = Query(None, description="Filter by product UUID"),
    category_def_id: Optional[UUID] = Query(None, description="Filter by category UUID"),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquiryUnreadResponse:
    """
    Inquiries with status='submitted' (not yet acknowledged).
    Filterable by priority, department, service, product, category.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_inquiry_unread(
        project_id, priority=priority,
        department_id=department_id, service_id=service_id,
        product_id=product_id, category_def_id=category_def_id,
    )
    items = [
        InquiryUnreadItem(
            feedback_id     = r["feedback_id"],
            unique_ref      = r.get("unique_ref"),
            priority        = r.get("priority"),
            submitted_at    = r.get("submitted_at"),
            days_waiting    = float(r["days_waiting"]) if r.get("days_waiting") is not None else None,
            channel         = r.get("channel"),
            issue_lga       = r.get("issue_lga"),
            department_id   = r.get("department_id"),
            service_id      = r.get("service_id"),
            product_id      = r.get("product_id"),
            category_def_id = r.get("category_def_id"),
        )
        for r in rows
    ]
    return InquiryUnreadResponse(total=len(items), items=items)


# ── GET /analytics/inquiries/overdue ─────────────────────────────────────────

@router.get("/overdue", response_model=InquiryOverdueResponse)
async def get_inquiry_overdue(
    project_id:      UUID           = Query(...),
    department_id:   Optional[UUID] = Query(None),
    service_id:      Optional[UUID] = Query(None),
    product_id:      Optional[UUID] = Query(None),
    category_def_id: Optional[UUID] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquiryOverdueResponse:
    """
    Inquiries in acknowledged/in_review status past their target_resolution_date.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    rows = await repo.get_inquiry_overdue(
        project_id,
        department_id=department_id, service_id=service_id,
        product_id=product_id, category_def_id=category_def_id,
    )
    items = [
        InquiryOverdueItem(
            feedback_id            = r["feedback_id"],
            unique_ref             = r.get("unique_ref"),
            priority               = r.get("priority"),
            status                 = r.get("status"),
            submitted_at           = r.get("submitted_at"),
            target_resolution_date = r.get("target_resolution_date"),
            days_overdue           = float(r["days_overdue"]) if r.get("days_overdue") is not None else None,
            assigned_to_user_id    = r.get("assigned_to_user_id"),
            department_id          = r.get("department_id"),
            service_id             = r.get("service_id"),
            product_id             = r.get("product_id"),
            category_def_id        = r.get("category_def_id"),
        )
        for r in rows
    ]
    return InquiryOverdueResponse(total=len(items), items=items)


# ── GET /analytics/inquiries/by-channel ──────────────────────────────────────

@router.get("/by-channel", response_model=InquiryByChannelResponse)
async def get_inquiry_by_channel(
    project_id: UUID          = Query(...),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquiryByChannelResponse:
    """
    Inquiry counts grouped by intake channel.
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_inquiry_by_channel(project_id, date_from=d_from, date_to=d_to)
    items = [
        InquiryByChannelItem(
            channel    = r["channel"],
            total      = int(r.get("total", 0)),
            open_count = int(r.get("open_count", 0)),
            resolved   = int(r.get("resolved", 0)),
        )
        for r in rows
    ]
    return InquiryByChannelResponse(total_items=len(items), items=items)


# ── GET /analytics/inquiries/by-category ─────────────────────────────────────

@router.get("/by-category", response_model=InquiryByCategoryResponse)
async def get_inquiry_by_category(
    project_id: UUID          = Query(...),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    _token: StaffDep = None,
    fb_db:  FeedbackDbDep = None,
) -> InquiryByCategoryResponse:
    """
    Inquiry counts grouped by dynamic category (category_def_id).
    """
    repo = FeedbackAnalyticsRepository(fb_db)
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to   = date.fromisoformat(date_to)   if date_to   else None
    rows = await repo.get_inquiry_by_category(project_id, date_from=d_from, date_to=d_to)
    items = [
        InquiryByCategoryItem(
            category_def_id     = r.get("category_def_id"),
            category_name       = r.get("category_name") or "uncategorised",
            category_slug       = r.get("category_slug"),
            total               = int(r.get("total", 0)),
            open_count          = int(r.get("open_count", 0)),
            resolved            = int(r.get("resolved", 0)),
            avg_response_hours  = float(r["avg_response_hours"]) if r.get("avg_response_hours") is not None else None,
        )
        for r in rows
    ]
    return InquiryByCategoryResponse(total_items=len(items), items=items)
