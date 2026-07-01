"""api/v1/internal.py — analytics_service internal endpoints (service-to-service only)"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from core.dependencies import AnalyticsDbDep, FeedbackDbDep, require_internal_key
from models.analytics import HotspotAlert
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository

log = structlog.get_logger(__name__)

# All routes in this module are secured by X-Service-Key at the router level.
router = APIRouter(
    prefix="/internal/analytics",
    tags=["Internal — Analytics"],
    dependencies=[Depends(require_internal_key)],
)


# ── GET /api/v1/internal/analytics/{org_id}/hotspots ─────────────────────────

@router.get("/{org_id}/hotspots", summary="[Internal] Active hotspots for an org (no staff JWT)")
async def get_org_hotspots(
    org_id:    UUID,
    fb_db:     FeedbackDbDep,
    an_db:     AnalyticsDbDep,
    days:      int = Query(default=30, ge=1, le=365,
                           description="Look-back window in calendar days"),
    min_count: int = Query(default=3, ge=1,
                           description="Minimum grievances in window to qualify as a hotspot"),
) -> dict:
    """
    Return active complaint hotspots for an organisation without requiring a staff JWT.

    Used by the AI service to query systemic complaint patterns so it can produce
    contextualised recommendations and risk summaries.

    Steps:
      1. Resolve org_id → project UUIDs (via feedback_db fb_projects table).
      2. Query analytics_db hotspot_alerts for those projects, filtering by the
         look-back window and minimum count threshold.
      3. Return hotspot records ordered by spike_factor descending (worst first).

    Returns an empty list when the org has no projects or no qualifying hotspots.
    """
    # 1 — resolve org → projects
    fb_repo     = FeedbackAnalyticsRepository(fb_db)
    project_ids = await fb_repo.get_project_ids_for_org(org_id)
    if not project_ids:
        return {"org_id": str(org_id), "days": days, "min_count": min_count, "total": 0, "hotspots": []}

    # 2 — query hotspot_alerts with date + count filters
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(HotspotAlert)
        .where(HotspotAlert.project_id.in_(project_ids))
        .where(HotspotAlert.alert_status == "active")
        .where(HotspotAlert.window_start >= since)
        .where(HotspotAlert.count_in_window >= min_count)
        .order_by(HotspotAlert.spike_factor.desc())
    )
    result  = await an_db.execute(q)
    records = list(result.scalars().all())

    # 3 — serialise
    hotspots = [
        {
            "id":           str(r.id),
            "project_id":   str(r.project_id),
            "location":     r.location,
            "category":     r.category,
            "count":        r.count_in_window,
            "spike_factor": r.spike_factor,
            "baseline_avg": r.baseline_avg,
            "alert_status": r.alert_status,
            "first_seen":   r.window_start.isoformat(),
            "last_seen":    r.window_end.isoformat(),
        }
        for r in records
    ]

    return {
        "org_id":    str(org_id),
        "days":      days,
        "min_count": min_count,
        "total":     len(hotspots),
        "hotspots":  hotspots,
    }
