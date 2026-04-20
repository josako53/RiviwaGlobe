"""
api/v1/internal_orgs.py — Internal service-to-service endpoints for org context.
═══════════════════════════════════════════════════════════════════════════════
Authentication: X-Service-Key header (same shared secret as channel-register).
These endpoints are NOT exposed through the public API — Nginx should block them
from external traffic in production.

Endpoints
─────────
  GET /api/v1/internal/orgs/{org_id}/ai-context
      Returns a compact org profile for AI insights enrichment:
      display_name, description, org_type, branches (name/status),
      published FAQs, departments (id/name), services (id/title/type).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_db

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/internal", tags=["Internal — Service-to-Service"])

_SERVICE_KEY = getattr(settings, "INTERNAL_SERVICE_KEY", "change-me-in-env")


def _require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    if x_service_key != _SERVICE_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key.")


# ─────────────────────────────────────────────────────────────────────────────
# GET /internal/orgs/{org_id}/ai-context
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/orgs/{org_id}/ai-context",
    summary="[Internal] Compact org profile for AI insights enrichment",
    dependencies=[Depends(_require_service_key)],
)
async def get_org_ai_context(
    org_id: uuid.UUID,
    db:     AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns organisation identity, published FAQs, active branches,
    departments, and services.  Used by analytics_service to enrich
    AI context with human-readable names before sending to Groq.
    """
    from sqlalchemy import text

    org_id_str = str(org_id)

    # ── Core profile ──────────────────────────────────────────────────────────
    org_row = (await db.execute(
        text("""
            SELECT id, legal_name, display_name, description, org_type,
                   status, country_code, website_url, support_email,
                   is_verified
            FROM organisations
            WHERE id = :org_id AND deleted_at IS NULL
        """),
        {"org_id": org_id_str},
    )).mappings().first()

    if not org_row:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    # ── Published FAQs ────────────────────────────────────────────────────────
    faq_rows = (await db.execute(
        text("""
            SELECT question, answer, display_order
            FROM org_faqs
            WHERE organisation_id = :org_id AND is_published = true
            ORDER BY display_order
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Active branches ───────────────────────────────────────────────────────
    branch_rows = (await db.execute(
        text("""
            SELECT id, name, code, branch_type, status, parent_branch_id
            FROM org_branches
            WHERE organisation_id = :org_id AND status = 'active'
            ORDER BY name
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Departments ───────────────────────────────────────────────────────────
    dept_rows = (await db.execute(
        text("""
            SELECT id, name, code, is_active
            FROM org_departments
            WHERE org_id = :org_id AND is_active = true
            ORDER BY sort_order, name
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Services & Products ───────────────────────────────────────────────────
    service_rows = (await db.execute(
        text("""
            SELECT id, title, slug, service_type, status, summary, category
            FROM org_services
            WHERE organisation_id = :org_id
              AND status NOT IN ('archived', 'draft')
            ORDER BY service_type, title
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    return {
        "org_id":        str(org_row["id"]),
        "legal_name":    org_row["legal_name"],
        "display_name":  org_row["display_name"],
        "description":   org_row["description"],
        "org_type":      org_row["org_type"],
        "status":        org_row["status"],
        "country_code":  org_row["country_code"],
        "website_url":   org_row["website_url"],
        "support_email": org_row["support_email"],
        "is_verified":   org_row["is_verified"],
        "faqs": [
            {
                "question": r["question"],
                "answer":   r["answer"],
            }
            for r in faq_rows
        ],
        "branches": [
            {
                "id":          str(r["id"]),
                "name":        r["name"],
                "code":        r["code"],
                "branch_type": r["branch_type"],
                "is_root":     r["parent_branch_id"] is None,
            }
            for r in branch_rows
        ],
        "departments": [
            {
                "id":   str(r["id"]),
                "name": r["name"],
                "code": r["code"],
            }
            for r in dept_rows
        ],
        "services": [
            {
                "id":           str(r["id"]),
                "title":        r["title"],
                "service_type": r["service_type"],
                "category":     r["category"],
                "summary":      r["summary"],
            }
            for r in service_rows
        ],
    }
