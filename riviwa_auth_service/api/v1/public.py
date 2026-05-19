"""
api/v1/public.py — Public organisation discovery endpoints (no authentication).

Consumers land here after scanning a QR code, tapping a shared link, or clicking
"View more details" on a verification result.  No JWT required — these are read-only
views of published, public-facing org data.

Routes
──────
  GET /public/orgs/{org_id}                 Org profile (name, logo, type, contact, verified)
  GET /public/orgs/{org_id}/branches        Active branches with locations
  GET /public/orgs/{org_id}/services        Published services with media & FAQs
  GET /public/orgs/{org_id}/projects        Active public projects
  GET /public/orgs/{org_id}/products        Published products (via product_service)
  GET /public/orgs/{org_id}/discover        All of the above in one call
"""
from __future__ import annotations

import uuid
from typing import Optional

import httpx
import structlog
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import get_db
from models.org_project import OrgProject, ProjectStatus, ProjectVisibility
from models.organisation import Organisation, OrgStatus
from models.organisation_extended import (
    BranchStatus, OrgBranch, OrgLocation, OrgService, OrgServiceFAQ,
    OrgServiceMedia, OrgServiceStatus,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/public", tags=["Public — Org Discovery"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL


# ── helpers ───────────────────────────────────────────────────────────────────

async def _get_org_or_404(org_id: uuid.UUID, db: AsyncSession) -> Organisation:
    org = await db.get(Organisation, org_id)
    if not org or org.status != OrgStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return org


def _org_out(org: Organisation) -> dict:
    return {
        "org_id":        str(org.id),
        "display_name":  org.display_name,
        "legal_name":    org.legal_name,
        "slug":          org.slug,
        "org_type":      org.org_type.value if hasattr(org.org_type, "value") else org.org_type,
        "logo_url":      org.logo_url,
        "description":   org.description,
        "website_url":   org.website_url,
        "support_email": org.support_email,
        "support_phone": org.support_phone,
        "is_verified":   org.is_verified,
        "verified_at":   org.verified_at.isoformat() if org.verified_at else None,
        "sms_code":      org.sms_code,
    }


def _branch_out(b: OrgBranch, locations: list) -> dict:
    return {
        "branch_id":   str(b.id),
        "name":        b.name,
        "code":        b.code,
        "branch_type": b.branch_type,
        "status":      b.status.value if hasattr(b.status, "value") else b.status,
        "phone":       b.phone,
        "email":       b.email,
        "opened_on":   b.opened_on.isoformat() if b.opened_on else None,
        "locations": [
            {
                "label":     loc.label,
                "city":      loc.city,
                "region":    loc.region,
                "country":   loc.country_code,
                "latitude":  loc.latitude,
                "longitude": loc.longitude,
                "is_primary": loc.is_primary,
            }
            for loc in locations if str(loc.branch_id) == str(b.id)
        ],
    }


def _service_out(s: OrgService, media: list, faqs: list) -> dict:
    svc_id = str(s.id)
    return {
        "service_id":      svc_id,
        "title":           s.title,
        "slug":            s.slug,
        "service_type":    s.service_type,
        "delivery_mode":   s.delivery_mode,
        "summary":         s.summary,
        "category":        s.category,
        "subcategory":     s.subcategory,
        "tags":            s.tags,
        "base_price":      s.base_price,
        "currency_code":   s.currency_code,
        "price_is_negotiable": s.price_is_negotiable,
        "delivery_time_days": s.delivery_time_days,
        "is_featured":     s.is_featured,
        "view_count":      s.view_count,
        "published_at":    s.published_at.isoformat() if s.published_at else None,
        "media": [
            {"url": m.media_url, "media_type": m.media_type,
             "is_cover": m.is_cover, "caption": m.caption}
            for m in media if str(m.service_id) == svc_id
        ],
        "faqs": [
            {"question": f.question, "answer": f.answer, "display_order": f.display_order}
            for f in faqs if str(f.service_id) == svc_id
        ],
    }


def _project_out(p: OrgProject) -> dict:
    return {
        "project_id":       str(p.id),
        "name":             p.name,
        "slug":             p.slug,
        "status":           p.status.value if hasattr(p.status, "value") else p.status,
        "category":         p.category,
        "sector":           p.sector,
        "description":      p.description,
        "objectives":       p.objectives,
        "region":           p.region,
        "location_description": p.location_description,
        "cover_image_url":  p.cover_image_url,
        "funding_source":   p.funding_source,
        "planned_start_date": p.planned_start_date.isoformat() if p.planned_start_date else None,
        "planned_end_date":   p.planned_end_date.isoformat()   if p.planned_end_date   else None,
    }


async def _fetch_products(org_id: str) -> list:
    """Call product_service public endpoint (no auth needed for published products)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{_PRODUCT_SERVICE_URL}/api/v1/public/products",
                params={"org_id": org_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("products", data) if isinstance(data, dict) else data
    except Exception as exc:
        log.warning("public.products_fetch_failed", org_id=org_id, error=str(exc))
    return []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}", summary="Public org profile")
async def get_org_profile(org_id: uuid.UUID, db: DbDep) -> dict:
    """
    Returns the public-facing profile of an organisation: name, logo, description,
    contact details, verification status, and SMS code for QR verification.
    No authentication required.
    """
    org = await _get_org_or_404(org_id, db)
    return _org_out(org)


@router.get("/orgs/{org_id}/branches", summary="Public branch list with locations")
async def get_org_branches(
    org_id:      uuid.UUID,
    db:          DbDep,
    branch_type: Optional[str] = Query(default=None),
) -> dict:
    """
    Returns all active branches for the organisation, each with its physical locations
    (address, city, region, GPS coordinates). Useful for store-locator features.
    """
    await _get_org_or_404(org_id, db)

    branch_q = select(OrgBranch).where(
        OrgBranch.organisation_id == org_id,
        OrgBranch.status == BranchStatus.ACTIVE,
    )
    if branch_type:
        branch_q = branch_q.where(OrgBranch.branch_type == branch_type)
    branch_q = branch_q.order_by(OrgBranch.name)

    branches  = (await db.execute(branch_q)).scalars().all()
    loc_q     = select(OrgLocation).where(OrgLocation.organisation_id == org_id)
    locations = (await db.execute(loc_q)).scalars().all()

    return {
        "org_id":   str(org_id),
        "branches": [_branch_out(b, locations) for b in branches],
        "total":    len(branches),
    }


@router.get("/orgs/{org_id}/services", summary="Published services")
async def get_org_services(
    org_id:   uuid.UUID,
    db:       DbDep,
    category: Optional[str] = Query(default=None),
    featured: Optional[bool] = Query(default=None),
) -> dict:
    """
    Returns all published (ACTIVE) services offered by this organisation,
    including cover media, pricing, delivery mode, and FAQs.
    """
    await _get_org_or_404(org_id, db)

    svc_q = select(OrgService).where(
        OrgService.organisation_id == org_id,
        OrgService.status == OrgServiceStatus.ACTIVE.value,
    )
    if category:
        svc_q = svc_q.where(OrgService.category == category)
    if featured is not None:
        svc_q = svc_q.where(OrgService.is_featured == featured)
    svc_q = svc_q.order_by(OrgService.is_featured.desc(), OrgService.view_count.desc())

    services = (await db.execute(svc_q)).scalars().all()

    if not services:
        return {"org_id": str(org_id), "services": [], "total": 0}

    service_ids = [s.id for s in services]

    media_q = select(OrgServiceMedia).where(OrgServiceMedia.service_id.in_(service_ids))
    media   = (await db.execute(media_q)).scalars().all()

    faq_q = select(OrgServiceFAQ).where(
        OrgServiceFAQ.service_id.in_(service_ids),
        OrgServiceFAQ.is_published == True,
    ).order_by(OrgServiceFAQ.display_order)
    faqs = (await db.execute(faq_q)).scalars().all()

    return {
        "org_id":   str(org_id),
        "services": [_service_out(s, media, faqs) for s in services],
        "total":    len(services),
    }


@router.get("/orgs/{org_id}/projects", summary="Active public projects")
async def get_org_projects(
    org_id:   uuid.UUID,
    db:       DbDep,
    category: Optional[str] = Query(default=None),
    sector:   Optional[str] = Query(default=None),
    region:   Optional[str] = Query(default=None),
    page:     int = Query(default=1, ge=1),
    size:     int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    Returns active projects that are publicly visible (ACTIVE status, PUBLIC visibility).
    Consumers can browse to find a project, submit feedback, or track progress.
    """
    await _get_org_or_404(org_id, db)

    q = select(OrgProject).where(
        OrgProject.organisation_id == org_id,
        OrgProject.status.in_([
            ProjectStatus.ACTIVE.value,
            ProjectStatus.PLANNING.value,
        ]),
        OrgProject.visibility == ProjectVisibility.PUBLIC.value,
    )
    if category:
        q = q.where(OrgProject.category == category)
    if sector:
        q = q.where(OrgProject.sector == sector)
    if region:
        q = q.where(OrgProject.region.ilike(f"%{region}%"))

    q = q.order_by(OrgProject.created_at.desc()).offset((page - 1) * size).limit(size)
    projects = (await db.execute(q)).scalars().all()

    return {
        "org_id":   str(org_id),
        "projects": [_project_out(p) for p in projects],
        "total":    len(projects),
        "page":     page,
    }


@router.get("/orgs/{org_id}/products", summary="Published products")
async def get_org_products(
    org_id:       uuid.UUID,
    db:           DbDep,
    product_type: Optional[str] = Query(default=None),
    page:         int = Query(default=1, ge=1),
    size:         int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    Returns published products from this organisation's catalog.
    Data is fetched from product_service — no authentication needed.
    """
    await _get_org_or_404(org_id, db)
    products = await _fetch_products(str(org_id))
    if product_type:
        products = [p for p in products if p.get("product_type") == product_type.upper()]
    # Apply simple pagination on the fetched list
    total = len(products)
    start = (page - 1) * size
    paged = products[start: start + size]
    return {
        "org_id":   str(org_id),
        "products": paged,
        "total":    total,
        "page":     page,
    }


@router.get("/orgs/{org_id}/discover", summary="Full org discovery — everything in one call")
async def discover_org(org_id: uuid.UUID, db: DbDep) -> dict:
    """
    Returns the complete public profile of an organisation in a single response:
    org details, branches (with locations), published services (with media & FAQs),
    active public projects, and published products.

    Designed for the consumer-facing 'Business Profile' screen — one network call
    loads everything needed to render the page.
    """
    org = await _get_org_or_404(org_id, db)
    oid = str(org_id)

    # Branches + locations
    branches  = (await db.execute(
        select(OrgBranch).where(
            OrgBranch.organisation_id == org_id,
            OrgBranch.status == BranchStatus.ACTIVE,
        ).order_by(OrgBranch.name)
    )).scalars().all()
    locations = (await db.execute(
        select(OrgLocation).where(OrgLocation.organisation_id == org_id)
    )).scalars().all()

    # Published services + their media + published FAQs
    services = (await db.execute(
        select(OrgService).where(
            OrgService.organisation_id == org_id,
            OrgService.status == OrgServiceStatus.ACTIVE.value,
        ).order_by(OrgService.is_featured.desc(), OrgService.view_count.desc())
    )).scalars().all()

    media: list = []
    faqs:  list = []
    if services:
        svc_ids = [s.id for s in services]
        media = (await db.execute(
            select(OrgServiceMedia).where(OrgServiceMedia.service_id.in_(svc_ids))
        )).scalars().all()
        faqs = (await db.execute(
            select(OrgServiceFAQ).where(
                OrgServiceFAQ.service_id.in_(svc_ids),
                OrgServiceFAQ.is_published == True,
            ).order_by(OrgServiceFAQ.display_order)
        )).scalars().all()

    # Active public projects
    projects = (await db.execute(
        select(OrgProject).where(
            OrgProject.organisation_id == org_id,
            OrgProject.status.in_([
                ProjectStatus.ACTIVE.value,
                ProjectStatus.PLANNING.value,
            ]),
            OrgProject.visibility == ProjectVisibility.PUBLIC.value,
        ).order_by(OrgProject.created_at.desc()).limit(20)
    )).scalars().all()

    # Products from product_service (async, non-blocking)
    products = await _fetch_products(oid)

    return {
        "org":      _org_out(org),
        "branches": [_branch_out(b, locations) for b in branches],
        "services": [_service_out(s, media, faqs) for s in services],
        "projects": [_project_out(p) for p in projects],
        "products": products[:20],
        "summary": {
            "branch_count":  len(branches),
            "service_count": len(services),
            "project_count": len(projects),
            "product_count": len(products),
        },
    }
