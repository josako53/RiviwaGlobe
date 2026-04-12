"""
api/v1/ai_insights.py — AI-powered natural language analytics insights.
Fetches relevant metrics based on context_type, then sends to Groq.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict
from uuid import UUID

import structlog
from fastapi import APIRouter

from core.dependencies import AnalyticsDbDep, CurrentUser, FeedbackDbDep
from repositories.analytics_repo import AnalyticsRepository
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import AIInsightRequest, AIInsightResponse
from services.ai_insights_service import ai_insights_service

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/ai", tags=["Analytics — AI Insights"])

# Valid context types and how they map to data-fetching strategies
_CONTEXT_TYPES = frozenset({
    "general",
    "grievances",
    "suggestions",
    "sla",
    "committees",
    "hotspots",
    "staff",
    "unresolved",
})


async def _build_context(
    context_type: str,
    project_id: UUID,
    fb_db: Any,
    an_db: Any,
) -> Dict[str, Any]:
    """
    Fetch relevant analytics data based on context_type.
    Returns a dict that will be serialised and sent to Groq.
    """
    fb_repo = FeedbackAnalyticsRepository(fb_db)
    an_repo = AnalyticsRepository(an_db)

    context: Dict[str, Any] = {
        "project_id": str(project_id),
        "context_type": context_type,
    }

    # Always include summary counts for all context types
    summary = await fb_repo.get_summary_counts(project_id)
    context["summary"] = summary

    if context_type in ("general", "grievances", "unresolved", "sla"):
        # Unresolved grievances
        unresolved = await fb_repo.get_unresolved_grievances(project_id)
        context["unresolved_grievances_count"] = len(unresolved)
        # Group by priority
        priority_counts: Dict[str, int] = {}
        for r in unresolved:
            p = r.get("priority") or "unknown"
            priority_counts[p] = priority_counts.get(p, 0) + 1
        context["unresolved_by_priority"] = priority_counts

    if context_type in ("general", "grievances", "sla"):
        # Overdue
        overdue = await fb_repo.get_overdue(project_id)
        context["overdue_count"] = len(overdue)

        # SLA pre-computed
        sla_records = await an_repo.get_sla_status(project_id, breached_only=False)
        if sla_records:
            total = len(sla_records)
            ack_breached = sum(1 for r in sla_records if r.ack_sla_breached)
            res_breached = sum(1 for r in sla_records if r.res_sla_breached)
            context["sla_total_records"]   = total
            context["sla_ack_breached"]    = ack_breached
            context["sla_res_breached"]    = res_breached
            context["sla_compliance_rate"] = round((total - res_breached) / total * 100, 2) if total > 0 else None

    if context_type in ("general", "suggestions"):
        # Suggestion implementation time
        impl_rows = await fb_repo.get_suggestion_implementation_time(project_id)
        hours = [
            float(r["hours_to_implement"])
            for r in impl_rows
            if r.get("hours_to_implement") is not None
        ]
        if hours:
            context["suggestion_avg_impl_hours"]    = round(sum(hours) / len(hours), 2)
            context["suggestion_median_impl_hours"] = round(statistics.median(hours), 2)
        context["suggestion_implemented_count"] = len(impl_rows)

        # Unread suggestions
        unread_sugg = await fb_repo.get_unread_suggestions(project_id)
        context["unread_suggestions_count"] = len(unread_sugg)

    if context_type in ("general", "hotspots"):
        # Hotspot alerts
        hotspots = await an_repo.get_hotspot_alerts(project_id, status="active")
        context["active_hotspot_count"] = len(hotspots)
        if hotspots:
            top_hotspot = hotspots[0]  # Already sorted by spike_factor desc
            context["top_hotspot"] = {
                "location":     top_hotspot.location,
                "category":     top_hotspot.category,
                "count":        top_hotspot.count_in_window,
                "spike_factor": top_hotspot.spike_factor,
            }

    if context_type in ("general", "committees"):
        # Committee performance
        committee_rows = await fb_repo.get_committee_performance(project_id)
        context["committee_count"] = len(committee_rows)
        if committee_rows:
            # Find lowest performing committee
            committees_with_rates = [
                r for r in committee_rows
                if r.get("resolution_rate") is not None
            ]
            if committees_with_rates:
                lowest = min(committees_with_rates, key=lambda r: float(r.get("resolution_rate", 0)))
                context["lowest_performing_committee"] = {
                    "name":            lowest.get("committee_name"),
                    "resolution_rate": float(lowest.get("resolution_rate", 0)),
                    "cases_overdue":   int(lowest.get("cases_overdue", 0)),
                }

    if context_type == "staff":
        # Staff unread assigned
        unread_staff = await fb_repo.get_staff_unread_assigned(project_id)
        context["staff_with_unread_assignments"] = len(unread_staff)
        context["total_unread_assigned_feedbacks"] = sum(
            int(r.get("unread_count", 0)) for r in unread_staff
        )

        # Logins today
        logins_today = await an_repo.get_logins_today_user_ids()
        context["staff_logged_in_today"] = len(logins_today)

    # Resolved today
    if context_type in ("general",):
        resolved_today = await fb_repo.get_resolved_today(project_id)
        context["resolved_today_count"] = len(resolved_today)

    return context


# ── POST /analytics/ai/ask ────────────────────────────────────────────────────

@router.post("/ask", response_model=AIInsightResponse)
async def ask_ai_insight(
    body:    AIInsightRequest,
    _token:  CurrentUser = None,
    fb_db:   FeedbackDbDep = None,
    an_db:   AnalyticsDbDep = None,
) -> AIInsightResponse:
    """
    Ask a natural language question about analytics data.
    The service fetches relevant metrics based on context_type, then sends
    the question and data to Groq (llama-3.3-70b-versatile) for an AI answer.

    context_type options: general | grievances | suggestions | sla | committees |
                          hotspots | staff | unresolved
    """
    ctx_type = body.context_type.lower()
    if ctx_type not in _CONTEXT_TYPES:
        ctx_type = "general"

    log.info(
        "analytics.ai_insights.ask",
        user_id=str(_token.sub),
        project_id=str(body.project_id),
        context_type=ctx_type,
    )

    context_data = await _build_context(
        context_type=ctx_type,
        project_id=body.project_id,
        fb_db=fb_db,
        an_db=an_db,
    )

    answer = await ai_insights_service.ask(
        question=body.question,
        context_data=context_data,
    )

    return AIInsightResponse(
        answer       = answer,
        context_used = context_data,
        model        = ai_insights_service.model_name,
    )
