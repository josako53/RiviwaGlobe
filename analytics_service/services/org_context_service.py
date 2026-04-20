"""
services/org_context_service.py — analytics_service
────────────────────────────────────────────────────────────────────────────
Fetches rich org context from auth_service's internal endpoint using the
X-Service-Key header.  Used by the AI insights context builders to include
org names, branches, FAQs, departments, and services in the Groq prompt.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

# Timeout for internal calls — short because both services are on the same Docker network
_TIMEOUT = httpx.Timeout(5.0)


class OrgContextService:
    """
    Fetches org profile data from auth_service for AI context enrichment.
    Failures are soft — returns minimal dict so AI insights can still run
    with whatever analytics data is available.
    """

    async def fetch_org_context(self, org_id: UUID) -> Dict[str, Any]:
        """
        Call GET /api/v1/internal/orgs/{org_id}/ai-context on auth_service.
        Returns the full org profile dict, or a minimal dict on failure.
        """
        url = f"{settings.AUTH_SERVICE_URL}/api/v1/internal/orgs/{org_id}/ai-context"
        headers = {"X-Service-Key": settings.INTERNAL_SERVICE_KEY}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            log.warning(
                "analytics.org_context.fetch_failed",
                org_id=str(org_id),
                status=resp.status_code,
            )
        except Exception as exc:
            log.warning(
                "analytics.org_context.fetch_error",
                org_id=str(org_id),
                error=str(exc),
            )
        return {"org_id": str(org_id)}

    def format_for_ai(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw auth_service response into a compact AI-friendly dict.
        Trims verbose fields, limits lists to reasonable sizes for token budget.
        """
        out: Dict[str, Any] = {
            "org_name":    raw.get("display_name") or raw.get("legal_name"),
            "legal_name":  raw.get("legal_name"),
            "org_type":    raw.get("org_type"),
            "description": raw.get("description"),
            "country":     raw.get("country_code"),
            "verified":    raw.get("is_verified"),
        }

        branches: List[Dict] = raw.get("branches", [])
        if branches:
            out["branches"] = [
                f"{b['name']} ({b.get('branch_type', 'branch')})"
                for b in branches[:20]  # cap at 20 for token budget
            ]
            out["branch_count"] = len(branches)

        faqs: List[Dict] = raw.get("faqs", [])
        if faqs:
            out["faqs"] = [
                {"q": f["question"], "a": f["answer"]}
                for f in faqs[:15]  # cap at 15 FAQs
            ]

        depts: List[Dict] = raw.get("departments", [])
        if depts:
            out["departments"] = [
                {"id": d["id"], "name": d["name"]}
                for d in depts
            ]

        services: List[Dict] = raw.get("services", [])
        if services:
            out["services"] = [
                {
                    "id":    s["id"],
                    "name":  s["title"],
                    "type":  s.get("service_type"),
                    "cat":   s.get("category"),
                }
                for s in services[:30]
            ]

        return {k: v for k, v in out.items() if v is not None}


org_context_service = OrgContextService()
