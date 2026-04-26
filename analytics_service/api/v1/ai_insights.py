"""
api/v1/ai_insights.py — AI-powered natural language analytics insights.
Fetches relevant metrics based on context_type/scope, then sends to Groq.

Scopes:
  project — queries by project_id (existing behaviour)
  org     — queries by org_id across all that org's projects
  platform — queries across ALL organisations
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException

from core.dependencies import AnalyticsDbDep, CurrentUser, FeedbackDbDep
from repositories.analytics_repo import AnalyticsRepository
from repositories.feedback_analytics_repo import FeedbackAnalyticsRepository
from schemas.analytics import AIInsightRequest, AIInsightResponse
from services.ai_insights_service import ai_insights_service
from services.org_context_service import org_context_service

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics/ai", tags=["Analytics — AI Insights"])

_PROJECT_CONTEXT_TYPES = frozenset({
    "general", "grievances", "suggestions", "sla", "committees", "hotspots", "staff", "unresolved",
    "inquiries",
})
_ORG_CONTEXT_TYPES = frozenset({
    "org_general", "org_grievances", "org_suggestions", "org_applause", "org_inquiries",
})
_PLATFORM_CONTEXT_TYPES = frozenset({
    "platform_general", "platform_grievances", "platform_suggestions", "platform_applause",
    "platform_inquiries",
})
_ALL_CONTEXT_TYPES = _PROJECT_CONTEXT_TYPES | _ORG_CONTEXT_TYPES | _PLATFORM_CONTEXT_TYPES


async def _build_project_context(context_type, project_id, fb_db, an_db) -> Dict[str, Any]:
    """Project-scoped context builder — enriched with project/org names and location."""
    fb_repo = FeedbackAnalyticsRepository(fb_db)
    an_repo = AnalyticsRepository(an_db)

    # ── Resolve human-readable project identity first ─────────────────────────
    profile = await fb_repo.get_project_profile(project_id)
    context: Dict[str, Any] = {
        "scope":        "project",
        "project_id":   str(project_id),
        "project_name": profile.get("name"),
        "org_id":       str(profile["organisation_id"]) if profile.get("organisation_id") else None,
        "org_name":     profile.get("org_display_name"),
        "sector":       profile.get("sector"),
        "category":     profile.get("category"),
        "region":       profile.get("region"),
        "primary_lga":  profile.get("primary_lga"),
        "country":      profile.get("country_code"),
        "project_status": str(profile["status"]) if profile.get("status") else None,
        "project_description": profile.get("description"),
        "context_type": context_type,
    }

    summary = await fb_repo.get_summary_counts(project_id)
    context["summary"] = summary

    if context_type in ("general", "grievances", "unresolved", "sla"):
        unresolved = await fb_repo.get_unresolved_grievances(project_id)
        context["unresolved_grievances_count"] = len(unresolved)
        priority_counts: Dict[str, int] = {}
        for r in unresolved:
            p = r.get("priority") or "unknown"
            priority_counts[p] = priority_counts.get(p, 0) + 1
        context["unresolved_by_priority"] = priority_counts

    if context_type in ("general", "grievances", "sla"):
        overdue = await fb_repo.get_overdue(project_id)
        context["overdue_count"] = len(overdue)
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
        impl_rows = await fb_repo.get_suggestion_implementation_time(project_id)
        hours = [float(r["hours_to_implement"]) for r in impl_rows if r.get("hours_to_implement") is not None]
        if hours:
            context["suggestion_avg_impl_hours"]    = round(sum(hours) / len(hours), 2)
            context["suggestion_median_impl_hours"] = round(statistics.median(hours), 2)
        context["suggestion_implemented_count"] = len(impl_rows)
        unread_sugg = await fb_repo.get_unread_suggestions(project_id)
        context["unread_suggestions_count"] = len(unread_sugg)

    if context_type in ("general", "hotspots"):
        hotspots = await an_repo.get_hotspot_alerts(project_id, status="active")
        context["active_hotspot_count"] = len(hotspots)
        if hotspots:
            top_hotspot = hotspots[0]
            context["top_hotspot"] = {
                "location":     top_hotspot.location,
                "category":     top_hotspot.category,
                "count":        top_hotspot.count_in_window,
                "spike_factor": top_hotspot.spike_factor,
            }

    if context_type in ("general", "committees"):
        committee_rows = await fb_repo.get_committee_performance(project_id)
        context["committee_count"] = len(committee_rows)
        if committee_rows:
            committees_with_rates = [r for r in committee_rows if r.get("resolution_rate") is not None]
            if committees_with_rates:
                lowest = min(committees_with_rates, key=lambda r: float(r.get("resolution_rate", 0)))
                context["lowest_performing_committee"] = {
                    "name":            lowest.get("committee_name"),
                    "resolution_rate": float(lowest.get("resolution_rate", 0)),
                    "cases_overdue":   int(lowest.get("cases_overdue", 0)),
                }

    if context_type == "staff":
        unread_staff = await fb_repo.get_staff_unread_assigned(project_id)
        context["staff_with_unread_assignments"] = len(unread_staff)
        context["total_unread_assigned_feedbacks"] = sum(int(r.get("unread_count", 0)) for r in unread_staff)
        logins_today = await an_repo.get_logins_today_user_ids()
        context["staff_logged_in_today"] = len(logins_today)

    if context_type == "general":
        resolved_today = await fb_repo.get_resolved_today(project_id)
        context["resolved_today_count"] = len(resolved_today)

    if context_type in ("general", "inquiries"):
        inquiry_summary = await fb_repo.get_inquiry_summary(project_id)
        context["inquiry_summary"] = inquiry_summary
        inquiry_unread = await fb_repo.get_inquiry_unread(project_id)
        context["inquiry_unread_count"] = len(inquiry_unread)

    return context


async def _build_org_context(context_type, org_id, fb_db) -> Dict[str, Any]:
    """Org-scoped context builder — enriched with org name, branches, FAQs, departments, services."""
    fb_repo = FeedbackAnalyticsRepository(fb_db)

    # ── Resolve org name from cached fb_projects, then enrich from auth ───────
    org_name = await fb_repo.get_org_name(org_id)
    raw_org  = await org_context_service.fetch_org_context(org_id)
    org_info = org_context_service.format_for_ai(raw_org)
    # Prefer auth-service name (authoritative) over cached name
    resolved_name = org_info.get("org_name") or org_name

    context: Dict[str, Any] = {
        "scope":        "org",
        "org_id":       str(org_id),
        "org_name":     resolved_name,
        "org_type":     org_info.get("org_type"),
        "description":  org_info.get("description"),
        "country":      org_info.get("country"),
        "verified":     org_info.get("verified"),
        "context_type": context_type,
    }

    # Include org structure so AI can reference real names in its answers
    if org_info.get("branches"):
        context["branches"]     = org_info["branches"]
        context["branch_count"] = org_info.get("branch_count", len(org_info["branches"]))
    if org_info.get("faqs"):
        context["faqs"] = org_info["faqs"]
    if org_info.get("departments"):
        context["departments"] = org_info["departments"]
    if org_info.get("services"):
        context["services"] = org_info["services"]

    # Always include org summary
    summary = await fb_repo.get_org_summary(org_id)
    context["summary"] = summary

    if context_type in ("org_general", "org_grievances"):
        grievance_summary = await fb_repo.get_org_grievance_summary(org_id)
        context["grievance_summary"] = grievance_summary
        sla_data = await fb_repo.get_org_grievance_sla(org_id)
        context["sla_overall_compliance_rate"] = sla_data.get("overall_compliance_rate")
        context["sla_total_breached"] = sla_data.get("total_breached", 0)
        context["sla_by_priority"] = sla_data.get("by_priority", [])
        by_level = await fb_repo.get_org_grievances_by_level(org_id)
        context["grievances_by_level"] = by_level

    if context_type in ("org_general", "org_suggestions"):
        suggestion_summary = await fb_repo.get_org_suggestion_summary(org_id)
        context["suggestion_summary"] = suggestion_summary

    if context_type in ("org_general", "org_applause"):
        applause = await fb_repo.get_org_applause_summary(org_id)
        context["applause_total"] = applause.get("total_applause", 0)
        context["applause_this_month"] = applause.get("this_month", 0)
        context["applause_mom_change"] = applause.get("mom_change")
        context["applause_top_categories"] = applause.get("top_categories", [])

    if context_type in ("org_general", "org_inquiries"):
        inquiry_summary = await fb_repo.get_org_inquiry_summary(org_id)
        context["inquiry_summary"] = inquiry_summary

    if context_type == "org_general":
        by_project = await fb_repo.get_org_by_project(org_id)
        context["by_project"] = by_project
        by_channel = await fb_repo.get_org_by_channel(org_id)
        context["by_channel"] = by_channel
        by_branch = await fb_repo.get_org_by_branch(org_id)
        if by_branch:
            context["by_branch"] = by_branch
        by_dept = await fb_repo.get_org_by_dimension(org_id, "department_id")
        if by_dept:
            context["by_department"] = by_dept
        by_service = await fb_repo.get_org_by_dimension(org_id, "service_id")
        if by_service:
            context["by_service"] = by_service
        by_product = await fb_repo.get_org_by_dimension(org_id, "product_id")
        if by_product:
            context["by_product"] = by_product
        by_category = await fb_repo.get_org_by_category(org_id)
        if by_category:
            context["by_category"] = by_category

    return context


async def _build_platform_context(context_type, fb_db) -> Dict[str, Any]:
    """Platform-wide context builder — top orgs include resolved names."""
    fb_repo = FeedbackAnalyticsRepository(fb_db)
    context: Dict[str, Any] = {
        "scope":        "platform",
        "context_type": context_type,
    }

    summary = await fb_repo.get_platform_summary()
    context["summary"] = summary

    if context_type in ("platform_general", "platform_grievances"):
        grievance_summary = await fb_repo.get_platform_grievance_summary()
        context["grievance_summary"] = grievance_summary
        sla_data = await fb_repo.get_platform_grievance_sla()
        context["sla_overall_compliance_rate"] = sla_data.get("overall_compliance_rate")
        context["sla_total_breached"] = sla_data.get("total_breached", 0)

    if context_type in ("platform_general", "platform_suggestions"):
        suggestion_summary = await fb_repo.get_platform_suggestion_summary()
        context["suggestion_summary"] = suggestion_summary

    if context_type in ("platform_general", "platform_applause"):
        applause = await fb_repo.get_platform_applause_summary()
        context["applause_total"]         = applause.get("total_applause", 0)
        context["applause_this_month"]    = applause.get("this_month", 0)
        context["applause_mom_change"]    = applause.get("mom_change")
        context["applause_top_categories"] = applause.get("top_categories", [])

    if context_type in ("platform_general", "platform_inquiries"):
        inquiry_summary = await fb_repo.get_platform_inquiry_summary()
        context["inquiry_summary"] = inquiry_summary

    if context_type == "platform_general":
        by_org = await fb_repo.get_platform_by_org()
        context["by_org_count"] = len(by_org)
        # org_name is already included from MAX(p.org_display_name) in the query
        context["top_orgs"] = [
            {
                "org_id":       str(r["organisation_id"]),
                "org_name":     r.get("org_name") or f"Org {str(r['organisation_id'])[:8]}",
                "total":        int(r.get("total", 0)),
                "grievances":   int(r.get("grievances", 0)),
                "suggestions":  int(r.get("suggestions", 0)),
                "applause":     int(r.get("applause", 0)),
                "inquiries":    int(r.get("inquiries", 0)),
                "unresolved":   int(r.get("unresolved", 0)),
            }
            for r in by_org[:5]  # top 5 by volume
        ]
        by_channel = await fb_repo.get_platform_by_channel()
        context["by_channel"] = by_channel

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

    Scope determines which data is fetched:
    - scope=project (default): requires project_id
      context_type: general | grievances | suggestions | sla | committees | hotspots | staff | unresolved
    - scope=org: requires org_id
      context_type: org_general | org_grievances | org_suggestions | org_applause
    - scope=platform: no project_id or org_id needed
      context_type: platform_general | platform_grievances | platform_suggestions | platform_applause
    """
    scope = body.scope.lower() if body.scope else "project"
    ctx_type = body.context_type.lower() if body.context_type else "general"

    # Validate and dispatch by scope
    if scope == "platform":
        if ctx_type not in _PLATFORM_CONTEXT_TYPES:
            ctx_type = "platform_general"
        context_data = await _build_platform_context(ctx_type, fb_db)

    elif scope == "org":
        if not body.org_id:
            raise HTTPException(status_code=422, detail="org_id is required for scope=org")
        if ctx_type not in _ORG_CONTEXT_TYPES:
            ctx_type = "org_general"
        context_data = await _build_org_context(ctx_type, body.org_id, fb_db)

    else:  # project (default)
        if not body.project_id:
            raise HTTPException(status_code=422, detail="project_id is required for scope=project")
        if ctx_type not in _PROJECT_CONTEXT_TYPES:
            ctx_type = "general"
        context_data = await _build_project_context(ctx_type, body.project_id, fb_db, an_db)

    log.info(
        "analytics.ai_insights.ask",
        user_id=str(_token.sub),
        scope=scope,
        project_id=str(body.project_id) if body.project_id else None,
        org_id=str(body.org_id) if body.org_id else None,
        context_type=ctx_type,
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
