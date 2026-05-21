"""
api/v1/dimension_analytics.py
────────────────────────────────────────────────────────────────────────────
Deep analytics per entity — product, service, branch, or department.

Endpoints (same pattern for all four dimensions)
────────────────────────────────────────────────────────────────────────────
  GET /analytics/products/{id}/summary     Full metrics + percentages
  GET /analytics/products/{id}/categories  Category distribution + percentages
  GET /analytics/products/{id}/themes      AI-mined themes from feedback text
  GET /analytics/products/{id}/feedback    Drill-down: paginated feedback list

  GET /analytics/services/{id}/summary
  GET /analytics/services/{id}/categories
  GET /analytics/services/{id}/themes
  GET /analytics/services/{id}/feedback

  GET /analytics/branches/{id}/summary
  GET /analytics/branches/{id}/categories
  GET /analytics/branches/{id}/themes
  GET /analytics/branches/{id}/feedback

  GET /analytics/departments/{id}/summary
  GET /analytics/departments/{id}/categories
  GET /analytics/departments/{id}/themes
  GET /analytics/departments/{id}/feedback
"""
from __future__ import annotations

import json
from datetime import date
from typing import Optional
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query, status

from core.config import settings
from core.dependencies import FeedbackDbDep, StaffDep
from repositories.dimension_analytics_repo import DimensionAnalyticsRepository
from schemas.dimension_analytics import (
    AIThemesResponse,
    CategoryDistributionResponse,
    DimensionSummaryResponse,
    FeedbackDrillDownResponse,
)

log    = structlog.get_logger(__name__)
router = APIRouter(tags=["Analytics — Products, Services, Branches, Departments"])

# ── AI theme extraction ───────────────────────────────────────────────────────

_THEME_SYSTEM = (
    "You are an analytics assistant. Given a list of customer feedback texts for a "
    "specific product, service, branch, or department, identify the top recurring "
    "themes or issues. For each theme:\n"
    "  - Give it a short name (2–5 words, title case)\n"
    "  - Count how many feedback items mention it\n"
    "  - Calculate its percentage of the total texts analysed\n\n"
    "Return ONLY valid JSON in this exact structure (no markdown, no prose):\n"
    '{"themes": [{"name": "Quality Issues", "count": 45, "pct": 89.1}, ...]}\n\n'
    "Rules: list at most 8 themes, sorted by count descending. "
    "If fewer than 5 texts are provided, return {\"themes\": [], \"note\": \"Insufficient data\"}."
)


async def _call_groq_themes(texts: list[str]) -> list[dict]:
    if not settings.GROQ_API_KEY:
        return []
    numbered = "\n".join(f"{i+1}. {t[:300]}" for i, t in enumerate(texts[:100]))
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _THEME_SYSTEM},
            {"role": "user",   "content": f"Feedback texts ({len(texts)} total):\n\n{numbered}"},
        ],
        "temperature": 0.2,
        "max_tokens":  512,
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}",
                         "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return data.get("themes", [])
    except Exception as exc:
        log.warning("dim_analytics.themes.groq_failed", error=str(exc))
        return []


# ── Generic handler factories ─────────────────────────────────────────────────

def _repo(fb_db) -> DimensionAnalyticsRepository:
    return DimensionAnalyticsRepository(fb_db)


def _make_summary_handler(dim: str):
    async def handler(
        entity_id: UUID,
        _token: StaffDep   = None,
        fb_db:  FeedbackDbDep = None,
        org_id:    Optional[UUID] = Query(default=None),
        date_from: Optional[date] = Query(default=None, description="YYYY-MM-DD"),
        date_to:   Optional[date] = Query(default=None, description="YYYY-MM-DD"),
    ) -> dict:
        data = await _repo(fb_db).get_summary(
            dim=dim, dim_id=entity_id,
            org_id=org_id, date_from=date_from, date_to=date_to,
        )
        result = {f"{dim}_id": str(entity_id), **data}
        # Append QR scan counts for products
        if dim == "product":
            scans = await _repo(fb_db).get_scan_counts("product", entity_id)
            result["qr_scans"] = scans
        return result
    return handler


def _make_categories_handler(dim: str):
    async def handler(
        entity_id: UUID,
        _token: StaffDep      = None,
        fb_db:  FeedbackDbDep = None,
        org_id:        Optional[UUID] = Query(default=None),
        feedback_type: Optional[str]  = Query(default=None, description="grievance | suggestion | applause | inquiry"),
        date_from:     Optional[date] = Query(default=None),
        date_to:       Optional[date] = Query(default=None),
    ) -> dict:
        cats = await _repo(fb_db).get_category_distribution(
            dim=dim, dim_id=entity_id,
            org_id=org_id, feedback_type=feedback_type,
            date_from=date_from, date_to=date_to,
        )
        return {
            f"{dim}_id": str(entity_id),
            "total_categorised": sum(c["count"] for c in cats if c["category_id"]),
            "categories": cats,
        }
    return handler


def _make_themes_handler(dim: str):
    async def handler(
        entity_id: UUID,
        _token: StaffDep      = None,
        fb_db:  FeedbackDbDep = None,
        limit: int = Query(default=80, ge=10, le=200,
                           description="Max feedback texts to analyse"),
    ) -> dict:
        texts = await _repo(fb_db).get_feedback_texts(dim=dim, dim_id=entity_id, limit=limit)
        if len(texts) < 5:
            return {
                f"{dim}_id": str(entity_id),
                "texts_analysed": len(texts),
                "themes": [],
                "note": "Not enough feedback to mine themes (minimum 5 required).",
            }
        themes = await _call_groq_themes(texts)
        return {
            f"{dim}_id": str(entity_id),
            "texts_analysed": len(texts),
            "themes": themes,
            "powered_by": "groq" if themes else None,
        }
    return handler


def _make_feedback_handler(dim: str):
    async def handler(
        entity_id: UUID,
        _token: StaffDep      = None,
        fb_db:  FeedbackDbDep = None,
        org_id:        Optional[UUID] = Query(default=None),
        feedback_type: Optional[str]  = Query(default=None,
            description="Filter by type: grievance | suggestion | applause | inquiry"),
        category_id:   Optional[UUID] = Query(default=None,
            description="Filter by category_def_id (click a category to drill down)"),
        status:        Optional[str]  = Query(default=None,
            description="Filter by status: SUBMITTED | ACKNOWLEDGED | IN_REVIEW | RESOLVED | CLOSED"),
        date_from:     Optional[date] = Query(default=None),
        date_to:       Optional[date] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=20, ge=1, le=100),
    ) -> dict:
        result = await _repo(fb_db).get_feedback_list(
            dim=dim, dim_id=entity_id,
            org_id=org_id,
            feedback_type=feedback_type,
            category_id=category_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page, size=size,
        )
        return {f"{dim}_id": str(entity_id), **result}
    return handler


# ── Register routes for all four dimensions ───────────────────────────────────

_DIMS = {
    "products":    "product",
    "services":    "service",
    "branches":    "branch",
    "departments": "department",
}

for _plural, _dim in _DIMS.items():
    _base = f"/analytics/{_plural}/{{entity_id}}"

    router.add_api_route(
        path=f"{_base}/summary",
        endpoint=_make_summary_handler(_dim),
        response_model=DimensionSummaryResponse,
        methods=["GET"],
        summary=f"{_dim.title()} summary — totals, type percentages, resolution rate, implementation rate",
        description=(
            f"Full analytics summary for a single {_dim}.\n\n"
            f"Returns:\n"
            f"- **total** feedback count\n"
            f"- **by_type**: grievance / suggestion / applause / inquiry counts + percentages\n"
            f"- **resolution_rate_pct**: % of all feedback resolved or closed\n"
            f"- **avg_resolution_hours**: mean hours to resolution\n"
            f"- **suggestion implementation_rate**: % of suggestions that were implemented\n"
            + ("- **qr_scans**: QR scan counts (AUTHENTIC / ALREADY_USED / UNRECOGNIZED)\n" if _dim == "product" else "")
        ),
        tags=[f"Analytics — {_dim.title()}"],
    )

    router.add_api_route(
        path=f"{_base}/categories",
        endpoint=_make_categories_handler(_dim),
        response_model=CategoryDistributionResponse,
        methods=["GET"],
        summary=f"{_dim.title()} category distribution — counts and percentages per category",
        description=(
            f"Returns each feedback category for the given {_dim}, with:\n"
            f"- **count** and **pct** (% of total for this {_dim})\n"
            f"- per-type breakdown (grievances, suggestions, applause, inquiries)\n"
            f"- avg resolution hours per category\n\n"
            f"E.g.: quality 89%, delivery speed 5%, customer care 6%\n\n"
            f"Use **category_id** from this response to call `/{_plural}/{{id}}/feedback` "
            f"for a drill-down list of all feedback in that category."
        ),
        tags=[f"Analytics — {_dim.title()}"],
    )

    router.add_api_route(
        path=f"{_base}/themes",
        endpoint=_make_themes_handler(_dim),
        response_model=AIThemesResponse,
        methods=["GET"],
        summary=f"{_dim.title()} AI-mined themes — recurring patterns from feedback text",
        description=(
            f"Sends up to `limit` recent feedback descriptions and voice transcriptions "
            f"to Groq LLM which identifies recurring themes and returns them with percentages.\n\n"
            f"Example output:\n"
            f'  [{{"name": "Quality Issues", "count": 45, "pct": 89.1}}, ...]\n\n'
            f"Requires GROQ_API_KEY to be configured. Returns empty themes list if not."
        ),
        tags=[f"Analytics — {_dim.title()}"],
    )

    router.add_api_route(
        path=f"{_base}/feedback",
        endpoint=_make_feedback_handler(_dim),
        response_model=FeedbackDrillDownResponse,
        methods=["GET"],
        summary=f"{_dim.title()} feedback drill-down — paginated list with filters",
        description=(
            f"Returns a paginated list of all feedback items for this {_dim}.\n\n"
            f"Filter by:\n"
            f"- **feedback_type** — `grievance | suggestion | applause | inquiry`\n"
            f"- **category_id**   — from the `/categories` endpoint (click a category → see its feedback)\n"
            f"- **status**        — `SUBMITTED | ACKNOWLEDGED | IN_REVIEW | RESOLVED | CLOSED`\n"
            f"- **date_from / date_to** — ISO date range\n\n"
            f"Typical use: user clicks 'Grievances' chip on the dashboard → calls this with "
            f"`?feedback_type=grievance`. User clicks a category bar → calls with `?category_id=...`."
        ),
        tags=[f"Analytics — {_dim.title()}"],
    )
