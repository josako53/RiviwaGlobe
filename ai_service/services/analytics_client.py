"""
services/analytics_client.py — Fetch live analytics snapshots from analytics_service.

Called by conversation_service._build_project_context() to enrich the LLM
system prompt with real-time grievance performance data for the active project.

All methods are fire-and-forget safe: they return empty strings on any error
so a slow or unavailable analytics_service never breaks a conversation.
"""
from __future__ import annotations

import uuid
from typing import Optional
import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

_TIMEOUT = 4  # seconds — must not block conversation turns


async def _get(url: str, token: str, params: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        log.warning("analytics_client.fetch_failed", url=url, error=str(exc))
    return {}


async def get_project_analytics_context(
    project_id: uuid.UUID,
    token: str,
) -> str:
    """
    Fetch project-level grievance dashboard + category + stage breakdowns.
    Returns a compact text block for injection into the LLM system prompt.
    """
    base = settings.ANALYTICS_SERVICE_URL

    dashboard = await _get(
        f"{base}/api/v1/analytics/grievances/dashboard",
        token,
        {"project_id": str(project_id), "page_size": 1},
    )
    if not dashboard:
        return ""

    by_category = await _get(
        f"{base}/api/v1/analytics/feedback/by-category",
        token,
        {"project_id": str(project_id), "feedback_type": "GRIEVANCE"},
    )
    by_stage = await _get(
        f"{base}/api/v1/analytics/feedback/by-stage",
        token,
        {"project_id": str(project_id)},
    )
    by_dept = await _get(
        f"{base}/api/v1/analytics/feedback/by-department",
        token,
        {"project_id": str(project_id)},
    )

    return _format_project_snapshot(dashboard, by_category, by_stage, by_dept)


async def get_org_analytics_context(
    org_id: uuid.UUID,
    token: str,
    project_id: Optional[uuid.UUID] = None,
) -> str:
    """
    Fetch org-level grievance dashboard.
    Returns a compact text block for injection into the LLM system prompt.
    """
    base = settings.ANALYTICS_SERVICE_URL
    params: dict = {}
    if project_id:
        params["project_id"] = str(project_id)

    dashboard = await _get(
        f"{base}/api/v1/analytics/org/{org_id}/grievances/dashboard",
        token,
        {**params, "page_size": 1},
    )
    if not dashboard:
        return ""

    by_branch = await _get(
        f"{base}/api/v1/analytics/org/{org_id}/by-branch",
        token,
        {"feedback_type": "GRIEVANCE"},
    )
    by_category = await _get(
        f"{base}/api/v1/analytics/org/{org_id}/by-category",
        token,
        {"feedback_type": "GRIEVANCE"},
    )

    return _format_org_snapshot(dashboard, by_branch, by_category)


def _format_project_snapshot(
    dashboard: dict,
    by_category: dict,
    by_stage: dict,
    by_dept: dict,
) -> str:
    s = dashboard.get("summary", {})
    if not s.get("total_grievances"):
        return ""

    lines = ["=== LIVE PROJECT ANALYTICS ==="]
    lines.append(f"Total grievances: {s.get('total_grievances', 0)}")
    lines.append(f"Unresolved: {s.get('unresolved', 0)}  |  Escalated: {s.get('escalated', 0)}")
    lines.append(f"Acknowledged: {s.get('acknowledged_pct') or 0:.1f}%")

    rot = s.get("resolved_on_time_pct")
    rlt = s.get("resolved_late_pct")
    if rot is not None:
        lines.append(f"Resolved on time: {rot:.1f}%  |  Resolved late: {rlt or 0:.1f}%")

    avg_h = s.get("avg_resolution_hours")
    if avg_h:
        lines.append(f"Avg resolution time: {avg_h:.1f}h")

    overdue = dashboard.get("overdue", [])
    if overdue:
        lines.append(f"Overdue grievances: {len(overdue)}")

    by_pri = dashboard.get("by_priority", [])
    if by_pri:
        pri_parts = [f"{r['priority']}: {r['total']}" for r in by_pri if r.get("total")]
        if pri_parts:
            lines.append("By priority: " + ", ".join(pri_parts))

    cats = (by_category.get("items") or [])[:5]
    if cats:
        cat_parts = [f"{c.get('category_name','?')}: {c.get('grievances', c.get('total', 0))}"
                     for c in cats if c.get("grievances") or c.get("total")]
        if cat_parts:
            lines.append("Top categories: " + ", ".join(cat_parts))

    stages = (by_stage.get("items") or [])
    if stages:
        stage_parts = [f"{st.get('stage_name','?')}: {st.get('grievances', 0)}" for st in stages]
        lines.append("By sub-project stage: " + ", ".join(stage_parts))

    depts = (by_dept.get("items") or [])
    if depts:
        dept_parts = [f"dept {d.get('department_id','')}:{d.get('grievances',0)}" for d in depts[:3]]
        lines.append("By department: " + ", ".join(dept_parts))

    return "\n".join(lines)


def _format_org_snapshot(
    dashboard: dict,
    by_branch: dict,
    by_category: dict,
) -> str:
    s = dashboard.get("summary", {})
    if not s.get("total_grievances"):
        return ""

    lines = ["=== LIVE ORG ANALYTICS ==="]
    lines.append(f"Total grievances across org: {s.get('total_grievances', 0)}")
    lines.append(f"Unresolved: {s.get('unresolved', 0)}  |  Escalated: {s.get('escalated', 0)}")
    lines.append(f"Acknowledged: {s.get('acknowledged_pct') or 0:.1f}%")

    rot = s.get("resolved_on_time_pct")
    if rot is not None:
        lines.append(f"Resolved on time: {rot:.1f}%  |  Resolved late: {s.get('resolved_late_pct') or 0:.1f}%")

    by_proj = dashboard.get("by_project", [])[:5]
    if by_proj:
        proj_parts = [f"{p.get('project_name','?')}: {p.get('total', 0)}" for p in by_proj]
        lines.append("By project: " + ", ".join(proj_parts))

    branches = (by_branch.get("items") or [])[:5]
    if branches:
        br_parts = [f"branch {b.get('dimension_id','')}:{b.get('grievances',0)}" for b in branches]
        lines.append("By branch: " + ", ".join(br_parts))

    cats = (by_category.get("items") or [])[:5]
    if cats:
        cat_parts = [f"{c.get('category_name','?')}: {c.get('grievances', 0)}" for c in cats]
        lines.append("Top categories: " + ", ".join(cat_parts))

    return "\n".join(lines)
