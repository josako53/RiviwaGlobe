"""
api/v1/internal_orgs.py — Internal service-to-service endpoints for org context.
═══════════════════════════════════════════════════════════════════════════════
Authentication: X-Service-Key header (same shared secret as channel-register).
These endpoints are NOT exposed through the public API — Nginx should block them
from external traffic in production.

Endpoints
─────────
  GET /api/v1/internal/orgs/{org_id}/ai-context
      Returns a compact org profile for AI insights enrichment.

  GET /api/v1/internal/departments/{dept_id}
      Returns dept id, name, and branch_id. Used by feedback_service to
      resolve branch_id at submission time when department_id is provided.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
import math

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_async_session as get_db

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

    # ── Industries ────────────────────────────────────────────────────────────
    industry_rows = (await db.execute(
        text("""
            SELECT i.id, i.name, i.slug, oi.is_primary
            FROM organisation_industries oi
            JOIN industries i ON i.id = oi.industry_id
            WHERE oi.org_id = :org_id AND i.is_active = true
            ORDER BY oi.is_primary DESC, i.name
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Operating hours ───────────────────────────────────────────────────────
    hours_rows = (await db.execute(
        text("""
            SELECT day_of_week, is_open, open_time, close_time, timezone, notes
            FROM org_operating_hours
            WHERE org_id = :org_id AND branch_id IS NULL
            ORDER BY CASE day_of_week::text
                WHEN 'MONDAY' THEN 1 WHEN 'TUESDAY' THEN 2 WHEN 'WEDNESDAY' THEN 3
                WHEN 'THURSDAY' THEN 4 WHEN 'FRIDAY' THEN 5 WHEN 'SATURDAY' THEN 6
                WHEN 'SUNDAY' THEN 7 END
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Published FAQs ────────────────────────────────────────────────────────
    faq_rows = (await db.execute(
        text("""
            SELECT question, answer, display_order
            FROM org_faqs
            WHERE org_id = :org_id AND is_published = true
            ORDER BY display_order
        """),
        {"org_id": org_id_str},
    )).mappings().all()

    # ── Active branches ───────────────────────────────────────────────────────
    branch_rows = (await db.execute(
        text("""
            SELECT b.id, b.name, b.code, b.branch_type, b.status, b.parent_branch_id,
                   b.phone, b.email,
                   ol.city, ol.region, ol.display_name AS address
            FROM org_branches b
            LEFT JOIN org_locations ol ON ol.branch_id = b.id
            WHERE b.organisation_id = :org_id AND b.status = 'ACTIVE'
            ORDER BY b.name
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

    # ── Services & Products (with price and description) ──────────────────────
    service_rows = (await db.execute(
        text("""
            SELECT id, title, slug, service_type, status, summary, description,
                   category, subcategory, base_price, currency_code, delivery_mode
            FROM org_services
            WHERE organisation_id = :org_id
              AND status NOT IN ('ARCHIVED', 'DRAFT')
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
        "industries": [
            {
                "id":         str(r["id"]),
                "name":       r["name"],
                "slug":       r["slug"],
                "is_primary": r["is_primary"],
            }
            for r in industry_rows
        ],
        "operating_hours": [
            {
                "day":      r["day_of_week"],
                "is_open":  r["is_open"],
                "open":     str(r["open_time"]) if r["open_time"] else None,
                "close":    str(r["close_time"]) if r["close_time"] else None,
                "timezone": r["timezone"],
                "notes":    r["notes"],
            }
            for r in hours_rows
        ],
        "faqs": [
            {"question": r["question"], "answer": r["answer"]}
            for r in faq_rows
        ],
        "branches": [
            {
                "id":          str(r["id"]),
                "name":        r["name"],
                "code":        r["code"],
                "branch_type": r["branch_type"],
                "is_root":     r["parent_branch_id"] is None,
                "phone":       r["phone"],
                "email":       r["email"],
                "city":        r["city"],
                "region":      r["region"],
                "address":     r["address"],
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
                "id":            str(r["id"]),
                "title":         r["title"],
                "slug":          r["slug"],
                "service_type":  r["service_type"],
                "category":      r["category"],
                "subcategory":   r["subcategory"],
                "summary":       r["summary"] or r["description"],
                "base_price":    float(r["base_price"]) if r["base_price"] is not None else None,
                "currency_code": r["currency_code"],
                "delivery_mode": r["delivery_mode"],
            }
            for r in service_rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /internal/departments/{dept_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/departments/{dept_id}",
    summary="[Internal] Resolve department branch_id",
    dependencies=[Depends(_require_service_key)],
)
async def get_department_internal(
    dept_id: uuid.UUID,
    db:      AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns id, name, code and branch_id for a single department.
    Called by feedback_service at submission time to denormalise
    branch_id onto the feedback row for branch-level analytics.
    """
    from sqlalchemy import text

    row = (await db.execute(
        text("""
            SELECT id, name, code, branch_id, org_id
            FROM org_departments
            WHERE id = :dept_id AND is_active = true
        """),
        {"dept_id": str(dept_id)},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Department not found.")

    return {
        "id":              str(row["id"]),
        "name":            row["name"],
        "code":            row["code"],
        "branch_id":       str(row["branch_id"]) if row["branch_id"] else None,
        "organisation_id": str(row["org_id"]) if row["org_id"] else None,
    }


# GET /internal/branches/{branch_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/branches/{branch_id}",
    summary="[Internal] Resolve branch organisation_id",
    dependencies=[Depends(_require_service_key)],
)
async def get_branch_internal(
    branch_id: uuid.UUID,
    db:        AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns id, name, code, and organisation_id for a single branch.
    Called by feedback_service to derive org_id from a consumer-provided
    branch_id (e.g. branch selected from UI or inferred from QR context).
    org_id is always derived from the child entity — never accepted directly.
    """
    from sqlalchemy import text

    row = (await db.execute(
        text("""
            SELECT id, name, code, organisation_id
            FROM org_branches
            WHERE id = :branch_id AND status = 'ACTIVE'
        """),
        {"branch_id": str(branch_id)},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Branch not found.")

    return {
        "id":              str(row["id"]),
        "name":            row["name"],
        "code":            row["code"],
        "organisation_id": str(row["organisation_id"]) if row["organisation_id"] else None,
    }


@router.get(
    "/orgs/{org_id}/sms-code",
    summary="[Internal] Get org SMS code prefix for QR service",
    dependencies=[Depends(_require_service_key)],
)
async def get_org_sms_code(
    org_id: uuid.UUID,
    db:     AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the org's sms_code (UTT, CRDB, TARURA etc.) and slug.
    Used by qr_service to derive the SMS prefix for QR codes.
    Format: {ORG_SMS_CODE}-{SHORT_CODE}  e.g.  TARURA-E2GVG8PT
    """
    from sqlalchemy import text
    row = (await db.execute(
        text("SELECT sms_code, slug, display_name FROM organisations WHERE id = :id"),
        {"id": str(org_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return {
        "sms_code":     row["sms_code"],
        "slug":         row["slug"],
        "display_name": row["display_name"],
    }


@router.get(
    "/orgs/{org_id}/owner-contact",
    summary="[Internal] Get org owner contact for notification dispatch",
    dependencies=[Depends(_require_service_key)],
)
async def get_org_owner_contact(
    org_id: uuid.UUID,
    db:     AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the org owner's user_id, email, phone, display_name, and language,
    plus the org display_name. Used by subscription_service to address
    billing/subscription notifications to the correct person.
    Falls back to first OWNER found; if none, returns org support_email.
    """
    from sqlalchemy import text
    row = (await db.execute(text("""
        SELECT
            u.id            AS user_id,
            u.email         AS email,
            u.phone_number  AS phone,
            u.display_name  AS display_name,
            u.language      AS language,
            o.display_name  AS org_name,
            o.support_email AS org_support_email
        FROM organisation_members om
        JOIN users         u ON u.id = om.user_id
        JOIN organisations o ON o.id = om.organisation_id
        WHERE om.organisation_id = :org_id
          AND om.org_role = 'OWNER'
          AND om.status   = 'ACTIVE'
          AND o.deleted_at IS NULL
        ORDER BY om.joined_at ASC
        LIMIT 1
    """), {"org_id": str(org_id)})).mappings().first()

    if row:
        return {
            "user_id":      str(row["user_id"]),
            "email":        row["email"],
            "phone":        row["phone"],
            "display_name": row["display_name"],
            "language":     row["language"] or "en",
            "org_name":     row["org_name"],
        }

    # Fallback — no active owner found (org may be admin-created)
    org = (await db.execute(text(
        "SELECT display_name, support_email FROM organisations WHERE id = :id AND deleted_at IS NULL"
    ), {"id": str(org_id)})).mappings().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return {
        "user_id":      None,
        "email":        org["support_email"],
        "phone":        None,
        "display_name": None,
        "language":     "en",
        "org_name":     org["display_name"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bulk-list endpoints for AI entity reindex
# ─────────────────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@router.get(
    "/organisations",
    summary="[Internal] Bulk list all organisations for entity reindex",
    dependencies=[Depends(_require_service_key)],
)
async def list_organisations_internal(
    limit: int = Query(default=500, ge=1, le=2000),
    skip:  int = Query(default=0, ge=0),
    db:    AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT o.id, o.legal_name, o.display_name, o.slug, o.sms_code, o.description,
                   o.org_type, o.status, o.country_code, o.timezone, o.website_url,
                   o.support_email, o.support_phone, o.is_verified,
                   oc.vision, oc.mission, oc.objectives, oc.functionalities,
                   oc.global_policy, oc.terms_of_use, oc.privacy_policy,
                   -- FAQs
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object('question', f.question, 'answer', f.answer)
                               ORDER BY f.display_order)
                        FROM org_faqs f
                        WHERE f.org_id = o.id AND f.is_published = true),
                       '[]'::jsonb
                   ) AS faqs,
                   -- Industries
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object(
                                   'id', i.id::text, 'name', i.name, 'slug', i.slug,
                                   'is_primary', oi.is_primary))
                        FROM organisation_industries oi
                        JOIN industries i ON i.id = oi.industry_id
                        WHERE oi.org_id = o.id AND i.is_active = true),
                       '[]'::jsonb
                   ) AS industries,
                   -- Custom feedback field definitions
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object(
                                   'field_key', cfd.field_key,
                                   'label', cfd.label,
                                   'label_sw', cfd.label_sw,
                                   'field_type', cfd.field_type,
                                   'feedback_types', cfd.feedback_types,
                                   'is_required', cfd.is_required,
                                   'options', cfd.options,
                                   'sort_order', cfd.sort_order)
                               ORDER BY cfd.sort_order)
                        FROM org_custom_field_defs cfd
                        WHERE cfd.org_id = o.id
                          AND cfd.entity_type = 'feedback'
                          AND cfd.is_active = true),
                       '[]'::jsonb
                   ) AS feedback_form_fields,
                   -- Operating hours (org-wide)
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object(
                                   'day', oh.day_of_week::text,
                                   'is_open', oh.is_open,
                                   'open_time', oh.open_time::text,
                                   'close_time', oh.close_time::text,
                                   'break_start', oh.break_start::text,
                                   'break_end', oh.break_end::text,
                                   'timezone', oh.timezone,
                                   'notes', oh.notes)
                               ORDER BY CASE oh.day_of_week::text
                                   WHEN 'MONDAY'    THEN 1 WHEN 'TUESDAY'   THEN 2
                                   WHEN 'WEDNESDAY' THEN 3 WHEN 'THURSDAY'  THEN 4
                                   WHEN 'FRIDAY'    THEN 5 WHEN 'SATURDAY'  THEN 6
                                   WHEN 'SUNDAY'    THEN 7 END)
                        FROM org_operating_hours oh
                        WHERE oh.org_id = o.id AND oh.branch_id IS NULL),
                       '[]'::jsonb
                   ) AS operating_hours,
                   -- Leadership (public roles only)
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object(
                                   'id', lr.id::text,
                                   'full_name', lr.full_name,
                                   'role_title', lr.role_title,
                                   'scope', lr.scope::text,
                                   'duties', lr.duties,
                                   'department', lr.department,
                                   'phone', lr.phone,
                                   'email', lr.email,
                                   'level', lr.level,
                                   'parent_role_id', lr.parent_role_id::text,
                                   'is_public', lr.is_public)
                               ORDER BY lr.level, lr.sort_order)
                        FROM org_leadership_roles lr
                        WHERE lr.org_id = o.id
                          AND lr.branch_id IS NULL
                          AND lr.is_active = true),
                       '[]'::jsonb
                   ) AS leadership
            FROM organisations o
            LEFT JOIN org_content oc ON oc.org_id = o.id
            WHERE o.deleted_at IS NULL
            ORDER BY o.created_at
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip},
    )).mappings().all()
    return {
        "items": [
            {
                "id":             str(r["id"]),
                "name":           r["display_name"] or r["legal_name"],
                "legal_name":     r["legal_name"],
                "display_name":   r["display_name"],
                "slug":           r["slug"],
                "sms_code":       r["sms_code"],
                "description":    r["description"],
                "org_type":       r["org_type"],
                "status":         r["status"],
                "country_code":   r["country_code"],
                "timezone":       r["timezone"],
                "website_url":    r["website_url"],
                "support_email":  r["support_email"],
                "support_phone":  r["support_phone"],
                "is_verified":    r["is_verified"],
                "vision":               r["vision"],
                "mission":              r["mission"],
                "objectives":           r["objectives"],
                "functionalities":      list(r["functionalities"]) if r["functionalities"] else [],
                "global_policy":        r["global_policy"],
                "terms_of_use":         r["terms_of_use"],
                "privacy_policy":       r["privacy_policy"],
                "faqs":                 list(r["faqs"]) if r["faqs"] else [],
                "industries":           list(r["industries"]) if r["industries"] else [],
                "feedback_form_fields": list(r["feedback_form_fields"]) if r["feedback_form_fields"] else [],
                "operating_hours":      list(r["operating_hours"]) if r["operating_hours"] else [],
                "leadership":           list(r["leadership"]) if r["leadership"] else [],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get(
    "/branches",
    summary="[Internal] Bulk list all branches for entity reindex",
    dependencies=[Depends(_require_service_key)],
)
async def list_branches_internal(
    limit: int = Query(default=1000, ge=1, le=5000),
    skip:  int = Query(default=0, ge=0),
    db:    AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT b.id, b.name, b.code, b.description, b.branch_type,
                   b.status::text AS status, b.phone, b.email,
                   b.organisation_id,
                   ol.city, ol.region, ol.country_code,
                   ol.latitude, ol.longitude, ol.suburb, ol.display_name AS address
            FROM org_branches b
            LEFT JOIN org_locations ol ON ol.branch_id = b.id
            WHERE b.status::text != 'CLOSED'
            ORDER BY b.created_at
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip},
    )).mappings().all()
    return {
        "items": [
            {
                "id":          str(r["id"]),
                "name":        r["name"],
                "code":        r["code"],
                "description": r["description"],
                "branch_type": r["branch_type"],
                "status":      r["status"],
                "org_id":      str(r["organisation_id"]),
                "phone":       r["phone"],
                "email":       r["email"],
                "city":        r["city"],
                "region":      r["region"],
                "country":     r["country_code"],
                "address":     r["address"],
                "suburb":      r["suburb"],
                "latitude":    float(r["latitude"]) if r["latitude"] is not None else None,
                "longitude":   float(r["longitude"]) if r["longitude"] is not None else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get(
    "/departments",
    summary="[Internal] Bulk list all departments for entity reindex",
    dependencies=[Depends(_require_service_key)],
)
async def list_departments_internal(
    limit: int = Query(default=1000, ge=1, le=5000),
    skip:  int = Query(default=0, ge=0),
    db:    AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT id, name, code, description, org_id, branch_id, is_active, sort_order
            FROM org_departments
            WHERE is_active = true
            ORDER BY org_id, sort_order, name
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip},
    )).mappings().all()
    return {
        "items": [
            {
                "id":          str(r["id"]),
                "name":        r["name"],
                "code":        r["code"],
                "description": r["description"],
                "org_id":      str(r["org_id"]),
                "branch_id":   str(r["branch_id"]) if r["branch_id"] else None,
                "is_active":   r["is_active"],
                "sort_order":  r["sort_order"],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get(
    "/services",
    summary="[Internal] Bulk list all org services for entity reindex",
    dependencies=[Depends(_require_service_key)],
)
async def list_services_internal(
    limit: int = Query(default=1000, ge=1, le=5000),
    skip:  int = Query(default=0, ge=0),
    db:    AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT s.id, s.title, s.slug, s.service_type::text AS service_type,
                   s.status::text AS status,
                   s.summary, s.description, s.category, s.subcategory, s.tags,
                   s.delivery_mode::text AS delivery_mode,
                   s.product_format::text AS product_format,
                   s.base_price, s.currency_code,
                   s.is_featured, s.organisation_id, s.branch_id,
                   COALESCE(
                       (SELECT jsonb_agg(jsonb_build_object(
                           'is_virtual',       sl.is_virtual,
                           'virtual_platform', sl.virtual_platform,
                           'virtual_url',      sl.virtual_url,
                           'operating_hours',  sl.operating_hours,
                           'contact_phone',    sl.contact_phone,
                           'contact_email',    sl.contact_email,
                           'notes',            sl.notes,
                           'status',           sl.status::text
                        ))
                        FROM org_service_locations sl
                        WHERE sl.service_id = s.id AND sl.status::text = 'ACTIVE'),
                       '[]'::jsonb
                   ) AS locations,
                   COALESCE(
                       (SELECT jsonb_agg(jsonb_build_object(
                           'user_id',         sp.user_id::text,
                           'personnel_role',  sp.personnel_role::text,
                           'personnel_title', sp.personnel_title,
                           'is_primary',      sp.is_primary
                        ))
                        FROM org_service_personnel sp WHERE sp.service_id = s.id),
                       '[]'::jsonb
                   ) AS personnel,
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object('question', sf.question, 'answer', sf.answer)
                               ORDER BY sf.display_order)
                        FROM org_service_faqs sf
                        WHERE sf.service_id = s.id AND sf.is_published = true),
                       '[]'::jsonb
                   ) AS faqs
            FROM org_services s
            WHERE s.status::text NOT IN ('ARCHIVED', 'DRAFT')
            ORDER BY s.organisation_id, s.service_type, s.title
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip},
    )).mappings().all()
    return {
        "items": [
            {
                "id":             str(r["id"]),
                "title":          r["title"],
                "slug":           r["slug"],
                "service_type":   r["service_type"],
                "category":       r["category"],
                "subcategory":    r["subcategory"],
                "tags":           r["tags"] or [],
                "description":    r["description"] or r["summary"],
                "delivery_mode":  r["delivery_mode"],
                "product_format": r["product_format"],
                "base_price":     float(r["base_price"]) if r["base_price"] is not None else None,
                "currency_code":  r["currency_code"],
                "is_featured":    r["is_featured"],
                "status":         r["status"],
                "org_id":         str(r["organisation_id"]),
                "branch_id":      str(r["branch_id"]) if r["branch_id"] else None,
                "locations":      list(r["locations"]) if r["locations"] else [],
                "personnel":      list(r["personnel"]) if r["personnel"] else [],
                "faqs":           list(r["faqs"]) if r["faqs"] else [],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get(
    "/branches/{branch_id}/location",
    summary="[Internal] Get branch location and geofence for physically_verified check",
    dependencies=[Depends(_require_service_key)],
)
async def get_branch_location(
    branch_id: uuid.UUID,
    db:        AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the GPS coordinates and geofence radius for a single branch.
    Called by feedback_service at submission time to compute physically_verified:
    true when the submitter's GPS is within geofence_radius_m of the branch.
    """
    from sqlalchemy import text

    row = (await db.execute(
        text("""
            SELECT ol.latitude, ol.longitude, ol.geofence_radius_m, ol.boundary_polygon
            FROM org_locations ol
            WHERE ol.branch_id = :branch_id
            ORDER BY ol.is_primary DESC
            LIMIT 1
        """),
        {"branch_id": str(branch_id)},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="No location record for this branch.")

    return {
        "branch_id":         str(branch_id),
        "latitude":          float(row["latitude"])         if row["latitude"]         is not None else None,
        "longitude":         float(row["longitude"])        if row["longitude"]        is not None else None,
        "geofence_radius_m": int(row["geofence_radius_m"]) if row["geofence_radius_m"] is not None else None,
        "boundary_polygon":  row["boundary_polygon"],
    }


@router.get(
    "/orgs/{org_id}/hq-location",
    summary="[Internal] Get org headquarters location and geofence for physically_verified check",
    dependencies=[Depends(_require_service_key)],
)
async def get_org_hq_location(
    org_id: uuid.UUID,
    db:     AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the GPS coordinates, geofence radius, and boundary polygon for the
    organisation's primary headquarters location (branch_id IS NULL).
    Called by feedback_service when feedback has org_id but no branch_id —
    typically organisations with a single office / no branch structure.
    """
    from sqlalchemy import text

    row = (await db.execute(
        text("""
            SELECT ol.latitude, ol.longitude, ol.geofence_radius_m, ol.boundary_polygon
            FROM org_locations ol
            WHERE ol.organisation_id = :org_id AND ol.branch_id IS NULL
            ORDER BY ol.is_primary DESC
            LIMIT 1
        """),
        {"org_id": str(org_id)},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="No headquarters location for this organisation.")

    return {
        "org_id":            str(org_id),
        "latitude":          float(row["latitude"])         if row["latitude"]         is not None else None,
        "longitude":         float(row["longitude"])        if row["longitude"]        is not None else None,
        "geofence_radius_m": int(row["geofence_radius_m"]) if row["geofence_radius_m"] is not None else None,
        "boundary_polygon":  row["boundary_polygon"],
    }


@router.get(
    "/branches/{branch_id}/buildings",
    summary="[Internal] List buildings for a branch — used by feedback_service for building resolution",
    dependencies=[Depends(_require_service_key)],
)
async def get_branch_buildings(
    branch_id: uuid.UUID,
    db:        AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all active buildings for a branch with boundary_polygon and
    barometric ground_reference_hpa. feedback_service uses boundary_polygon
    to determine which building a GPS coordinate belongs to.
    """
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT id, name, code, gps_lat, gps_lng, boundary_polygon,
                   ground_altitude_m, ground_reference_hpa, reference_taken_at,
                   reference_station_id, total_floors
            FROM org_buildings
            WHERE branch_id = :branch_id AND is_active = true
            ORDER BY name
        """),
        {"branch_id": str(branch_id)},
    )).mappings().all()
    return [
        {
            "id":                   str(r["id"]),
            "name":                 r["name"],
            "code":                 r["code"],
            "gps_lat":              float(r["gps_lat"]) if r["gps_lat"] is not None else None,
            "gps_lng":              float(r["gps_lng"]) if r["gps_lng"] is not None else None,
            "boundary_polygon":     r["boundary_polygon"],
            "ground_altitude_m":    float(r["ground_altitude_m"]) if r["ground_altitude_m"] is not None else None,
            "ground_reference_hpa": float(r["ground_reference_hpa"]) if r["ground_reference_hpa"] is not None else None,
            "reference_taken_at":   r["reference_taken_at"].isoformat() if r["reference_taken_at"] else None,
            "reference_station_id": r["reference_station_id"],
            "total_floors":         r["total_floors"],
        }
        for r in rows
    ]


@router.get(
    "/buildings/{building_id}/floors",
    summary="[Internal] List calibrated floors for barometric floor detection",
    dependencies=[Depends(_require_service_key)],
)
async def get_building_floors(
    building_id: uuid.UUID,
    db:          AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all active floors with calibrated_pressure_hpa ordered by floor_number.
    feedback_service compares the user's phone pressure_hpa to each floor's
    calibrated_pressure_hpa and selects the closest match.
    Only floors with calibrated_pressure_hpa are returned (uncalibrated floors
    cannot participate in pressure-based floor detection).
    """
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT id, floor_number, floor_name, calibrated_pressure_hpa,
                   calibrated_at, floor_height_m, ceiling_height_m
            FROM org_floors
            WHERE building_id = :building_id
              AND is_active = true
              AND calibrated_pressure_hpa IS NOT NULL
            ORDER BY floor_number
        """),
        {"building_id": str(building_id)},
    )).mappings().all()
    return [
        {
            "id":                       str(r["id"]),
            "floor_number":             r["floor_number"],
            "floor_name":               r["floor_name"],
            "calibrated_pressure_hpa":  float(r["calibrated_pressure_hpa"]),
            "calibrated_at":            r["calibrated_at"].isoformat() if r["calibrated_at"] else None,
            "floor_height_m":           float(r["floor_height_m"]) if r["floor_height_m"] is not None else None,
            "ceiling_height_m":         float(r["ceiling_height_m"]) if r["ceiling_height_m"] is not None else None,
        }
        for r in rows
    ]


@router.get(
    "/floors/{floor_id}/pois",
    summary="[Internal] List active POIs on a floor for GPS nearest-match resolution",
    dependencies=[Depends(_require_service_key)],
)
async def get_floor_pois(
    floor_id: uuid.UUID,
    db:       AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all active POIs on the given floor that have a GPS coordinate.
    feedback_service uses Haversine nearest-match to resolve poi_id after
    floor detection. Only POIs with gps_lat/gps_lng are returned.
    """
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT id, zone_id, name, code, poi_type,
                   gps_lat, gps_lng, gps_accuracy_radius_m,
                   department_id, service_id,
                   is_emergency_point, nearest_emergency_poi_id
            FROM org_points_of_interest
            WHERE floor_id = :floor_id
              AND is_active = true
              AND gps_lat IS NOT NULL
              AND gps_lng IS NOT NULL
            ORDER BY name
        """),
        {"floor_id": str(floor_id)},
    )).mappings().all()
    return [
        {
            "id":                       str(r["id"]),
            "zone_id":                  str(r["zone_id"]) if r["zone_id"] else None,
            "name":                     r["name"],
            "code":                     r["code"],
            "poi_type":                 r["poi_type"],
            "gps_lat":                  float(r["gps_lat"]),
            "gps_lng":                  float(r["gps_lng"]),
            "gps_accuracy_radius_m":    r["gps_accuracy_radius_m"],
            "department_id":            str(r["department_id"]) if r["department_id"] else None,
            "service_id":               str(r["service_id"]) if r["service_id"] else None,
            "is_emergency_point":       r["is_emergency_point"],
            "nearest_emergency_poi_id": str(r["nearest_emergency_poi_id"]) if r["nearest_emergency_poi_id"] else None,
        }
        for r in rows
    ]


@router.get(
    "/orgs/{org_id}/branches-with-locations",
    summary="[Internal] List all branches for an org with GPS polygon — used by feedback_service to auto-resolve branch_id from GPS",
    dependencies=[Depends(_require_service_key)],
)
async def get_org_branches_with_locations(
    org_id: uuid.UUID,
    db:     AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all active branches for the org, each with its boundary_polygon and
    GPS centre. feedback_service calls this when branch_id is not explicitly provided
    in the submission: it checks which branch polygon contains the user's GPS coordinate
    and uses that branch_id for building/floor/POI resolution.
    Only branches that have an org_location record are returned.
    """
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT ob.id AS branch_id, ob.name, ob.code AS branch_code,
                   ol.latitude, ol.longitude, ol.geofence_radius_m, ol.boundary_polygon
            FROM org_branches ob
            JOIN org_locations ol ON ol.branch_id = ob.id
            WHERE ob.organisation_id = :org_id
              AND ob.status = 'ACTIVE'
              AND ol.is_primary = true
            ORDER BY ob.name
        """),
        {"org_id": str(org_id)},
    )).mappings().all()
    return [
        {
            "branch_id":         str(r["branch_id"]),
            "name":              r["name"],
            "branch_code":       r["branch_code"],
            "latitude":          float(r["latitude"])         if r["latitude"]         is not None else None,
            "longitude":         float(r["longitude"])        if r["longitude"]        is not None else None,
            "geofence_radius_m": int(r["geofence_radius_m"]) if r["geofence_radius_m"] is not None else None,
            "boundary_polygon":  r["boundary_polygon"],
        }
        for r in rows
    ]


@router.get(
    "/locations/nearest",
    summary="[Internal] Find nearest branch(es) within radius for GPS resolution",
    dependencies=[Depends(_require_service_key)],
)
async def get_nearest_branches(
    lat:       float = Query(..., description="Latitude of the consumer"),
    lng:       float = Query(..., description="Longitude of the consumer"),
    radius_km: float = Query(default=2.0, description="Search radius in km"),
    org_id:    Optional[uuid.UUID] = Query(default=None),
    db:        AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns branches with geocoded locations sorted by Haversine distance from
    the given lat/lng.  Uses bounding-box pre-filter in SQL, exact Haversine in Python.
    """
    from sqlalchemy import text

    deg = radius_km / 111.0  # ~1 degree latitude ≈ 111 km
    params: dict = {
        "lat_min": lat - deg,
        "lat_max": lat + deg,
        "lng_min": lng - deg,
        "lng_max": lng + deg,
    }
    org_clause = ""
    if org_id:
        org_clause = "AND ob.organisation_id = :org_id"
        params["org_id"] = str(org_id)

    rows = (await db.execute(
        text(f"""
            SELECT
                ol.branch_id,
                ob.organisation_id AS org_id,
                ob.name  AS branch_name,
                ob.code  AS branch_code,
                ob.branch_type,
                ol.latitude,
                ol.longitude,
                ol.city,
                ol.region,
                ol.suburb,
                ol.country_code,
                ol.display_name
            FROM org_locations ol
            JOIN org_branches ob ON ob.id = ol.branch_id
            WHERE ol.latitude  IS NOT NULL
              AND ol.longitude IS NOT NULL
              AND ob.status::text = 'ACTIVE'
              AND ol.latitude  BETWEEN :lat_min AND :lat_max
              AND ol.longitude BETWEEN :lng_min AND :lng_max
              {org_clause}
        """),
        params,
    )).mappings().all()

    results = []
    for r in rows:
        dist = _haversine_km(lat, lng, float(r["latitude"]), float(r["longitude"]))
        if dist <= radius_km:
            results.append({
                "branch_id":   str(r["branch_id"]),
                "org_id":      str(r["org_id"]),
                "branch_name": r["branch_name"],
                "branch_code": r["branch_code"],
                "branch_type": r["branch_type"],
                "latitude":    float(r["latitude"]),
                "longitude":   float(r["longitude"]),
                "city":        r["city"],
                "region":      r["region"],
                "suburb":      r["suburb"],
                "country_code": r["country_code"],
                "display_name": r["display_name"],
                "distance_km":  round(dist, 3),
            })

    results.sort(key=lambda x: x["distance_km"])
    return results


# ─────────────────────────────────────────────────────────────────────────────
# GET /internal/orgs/search   — name-based org search for AI conversation
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/orgs/search",
    summary="[Internal] Search organisations by name for AI org resolution",
    dependencies=[Depends(_require_service_key)],
)
async def search_orgs(
    q:     str = Query(..., min_length=2, description="Name fragment to search"),
    limit: int = Query(default=5, ge=1, le=20),
    db:    AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Case-insensitive ILIKE search across display_name, legal_name, and sms_code.
    Used by channel_service when the AI extracts an org name from the user's message
    and needs to find the matching registered organisation.
    Returns only non-partial, non-deleted orgs.
    """
    from sqlalchemy import text
    rows = (await db.execute(
        text("""
            SELECT id, legal_name, display_name, slug, org_type, status,
                   country_code, sms_code, is_verified,
                   COALESCE(
                       (SELECT ol.city FROM org_locations ol
                        JOIN org_branches ob ON ob.id = ol.branch_id
                        WHERE ob.organisation_id = o.id AND ol.is_primary = true
                        LIMIT 1),
                       NULL
                   ) AS city
            FROM organisations o
            WHERE deleted_at IS NULL
              AND is_partial = false
              AND (
                  display_name ILIKE :q
                  OR legal_name  ILIKE :q
                  OR sms_code    ILIKE :q
              )
            ORDER BY
                CASE WHEN display_name ILIKE :exact THEN 0 ELSE 1 END,
                display_name
            LIMIT :limit
        """),
        {"q": f"%{q}%", "exact": q, "limit": limit},
    )).mappings().all()

    return [
        {
            "org_id":       str(r["id"]),
            "display_name": r["display_name"],
            "legal_name":   r["legal_name"],
            "slug":         r["slug"],
            "org_type":     r["org_type"],
            "status":       r["status"],
            "country_code": r["country_code"],
            "sms_code":     r["sms_code"],
            "is_verified":  r["is_verified"],
            "city":         r["city"],
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# POST /internal/orgs/partial — create a placeholder org from AI conversation
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/orgs/partial",
    status_code=201,
    summary="[Internal] Create a partial/placeholder org from AI conversation",
    dependencies=[Depends(_require_service_key)],
)
async def create_partial_org(
    body: Dict[str, Any],
    db:   AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Called by channel_service when a user submits feedback for an org that is
    not yet registered on Riviwa. Creates a minimal placeholder Organisation row
    with is_partial=True so the feedback can be recorded and linked.

    Body fields:
      suggested_name   str  (required) — the name the user mentioned
      created_by_id    str  (required) — UUID of the submitting user
      sector           str  (optional) — industry/sector mentioned
      city             str  (optional) — city/location mentioned
      source           str  (optional) — "ai_conversation" | "qr" etc.
      language         str  (optional) — conversation language

    Returns the new org_id and display_name.
    Idempotent: if a partial org with the same normalised name already exists,
    returns the existing one and bumps partial_meta.feedback_count.
    """
    from sqlalchemy import text
    import re

    suggested_name = (body.get("suggested_name") or "").strip()
    if not suggested_name:
        raise HTTPException(status_code=400, detail="suggested_name is required.")

    created_by_id = body.get("created_by_id")
    if not created_by_id:
        raise HTTPException(status_code=400, detail="created_by_id is required.")

    # Idempotency: bidirectional containment — "Jumbo Night Market" matches
    # "Jumbo Night Market Mikocheni" and vice versa (LLM may extract a shorter form).
    # Two separate params (name1, name2) to avoid asyncpg duplicate-binding issues.
    existing = (await db.execute(
        text("""
            SELECT id, display_name, partial_meta
            FROM organisations
            WHERE is_partial = true
              AND deleted_at IS NULL
              AND (
                  display_name ILIKE '%' || :name1 || '%'
                  OR :name2 ILIKE '%' || display_name || '%'
              )
            LIMIT 1
        """),
        {"name1": suggested_name, "name2": suggested_name},
    )).mappings().first()

    if existing:
        # Bump feedback_count in meta
        meta = dict(existing["partial_meta"] or {})
        meta["feedback_count"] = int(meta.get("feedback_count", 0)) + 1
        await db.execute(
            text("UPDATE organisations SET partial_meta = CAST(:meta AS jsonb), updated_at = now() WHERE id = :id"),
            {"meta": __import__("json").dumps(meta), "id": str(existing["id"])},
        )
        await db.commit()
        return {"org_id": str(existing["id"]), "display_name": existing["display_name"], "is_new": False}

    # Generate a unique slug
    base_slug = re.sub(r"[^a-z0-9]+", "-", suggested_name.lower()).strip("-")
    import uuid as _uuid
    short = str(_uuid.uuid4())[:8]
    slug = f"partial-{base_slug}-{short}"

    # Partial meta
    meta = {
        "suggested_name":    suggested_name,
        "sector":            body.get("sector"),
        "city":              body.get("city"),
        "source":            body.get("source", "ai_conversation"),
        "language":          body.get("language", "en"),
        "submitter_user_id": body.get("created_by_id"),
        "feedback_count":    1,
    }

    new_id = str(_uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO organisations (
                id, legal_name, display_name, slug, org_type, status,
                is_verified, is_payment_verified, is_kyc_verified,
                is_partial, partial_meta, created_by_id, max_members,
                created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), :legal_name, :display_name, :slug, 'BUSINESS', 'PENDING_VERIFICATION',
                false, false, false,
                true, CAST(:meta AS jsonb), CAST(:created_by_id AS uuid), 0,
                now(), now()
            )
        """),
        {
            "id":             new_id,
            "legal_name":     suggested_name,
            "display_name":   suggested_name,
            "slug":           slug,
            "meta":           __import__("json").dumps(meta),
            "created_by_id":  created_by_id,
        },
    )
    await db.commit()
    log.info("partial_org.created", org_id=new_id, name=suggested_name)
    return {"org_id": new_id, "display_name": suggested_name, "is_new": True}
