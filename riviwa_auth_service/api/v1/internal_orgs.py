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
        "org_id": str(org_row["id"]),
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
            SELECT id, name, code, branch_id
            FROM org_departments
            WHERE id = :dept_id AND is_active = true
        """),
        {"dept_id": str(dept_id)},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Department not found.")

    return {
        "id":        str(row["id"]),
        "name":      row["name"],
        "code":      row["code"],
        "branch_id": str(row["branch_id"]) if row["branch_id"] else None,
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
                   oc.vision, oc.mission, oc.objectives,
                   oc.global_policy, oc.terms_of_use, oc.privacy_policy,
                   COALESCE(
                       (SELECT jsonb_agg(
                               jsonb_build_object('question', f.question, 'answer', f.answer)
                               ORDER BY f.display_order)
                        FROM org_faqs f
                        WHERE f.org_id = o.id AND f.is_published = true),
                       '[]'::jsonb
                   ) AS faqs
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
                "vision":         r["vision"],
                "mission":        r["mission"],
                "objectives":     r["objectives"],
                "global_policy":  r["global_policy"],
                "terms_of_use":   r["terms_of_use"],
                "privacy_policy": r["privacy_policy"],
                "faqs":           list(r["faqs"]) if r["faqs"] else [],
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
