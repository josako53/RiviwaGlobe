"""api/v1/internal.py — Internal and third-party API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from core.config import settings
from core.dependencies import ApiKeyDep, DbDep, InternalDep
from core.exceptions import StaffNotFoundError
from repositories.org_cache_repository import OrgCacheRepository
from repositories.staff_profile_repository import StaffProfileRepository
from schemas.staff_profile import StaffPublicOut

router = APIRouter(prefix="/api/v1/staff", tags=["Internal"])


def _require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key.")


# ── Sync Org ──────────────────────────────────────────────────────────────────

class SyncOrgBody(BaseModel):
    org_id: UUID
    name: str
    slug: Optional[str] = None
    is_active: bool = True


@router.post("/internal/sync-org", status_code=200)
async def sync_org(
    body: SyncOrgBody,
    db: DbDep,
    _: InternalDep,
) -> dict:
    """Upsert OrgCache from internal service call."""
    repo = OrgCacheRepository(db)
    org = await repo.upsert(body.org_id, {
        "name": body.name,
        "slug": body.slug,
        "is_active": body.is_active,
        "synced_at": datetime.utcnow(),
    })
    return {"org_id": str(org.org_id), "synced": True}


# ── Third-Party API Lookup ────────────────────────────────────────────────────

@router.get("/api/lookup/{code}", response_model=StaffPublicOut)
async def api_lookup_staff(
    code: str,
    db: DbDep,
    _: ApiKeyDep,
) -> StaffPublicOut:
    """
    Look up a staff member by code.
    Returns full StaffPublicOut or 404.
    Requires X-Api-Key header.
    """
    repo = StaffProfileRepository(db)
    profile = await repo.get_by_code_any_org(code)
    if not profile:
        raise StaffNotFoundError()
    hire_year = profile.hire_date.year if profile.hire_date else None
    return StaffPublicOut(
        staff_code=profile.staff_code,
        display_name=profile.display_name,
        position=profile.position,
        department=profile.department,
        branch_name=profile.branch_name,
        employment_type=profile.employment_type,
        is_verified=profile.is_verified,
        photo_url=profile.photo_url,
        org_id=profile.org_id,
        expertise=profile.expertise,
        hire_year=hire_year,
    )


# ── Bulk staff list for AI entity reindex ─────────────────────────────────────

@router.get(
    "/internal/staff",
    summary="[Internal] Bulk list active staff profiles for AI entity reindex",
    dependencies=[Depends(_require_service_key)],
)
async def list_staff_internal(
    db:    DbDep,
    limit: int = Query(default=1000, ge=1, le=5000),
    skip:  int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    from sqlalchemy import text

    rows = (await db.execute(
        text("""
            SELECT
                sp.id,
                sp.staff_code,
                sp.display_name,
                sp.position,
                sp.department,
                sp.branch_name,
                sp.employment_type,
                sp.is_verified,
                sp.is_active,
                sp.org_id,
                oc.name AS org_name
            FROM staff_profiles sp
            LEFT JOIN org_caches oc ON oc.org_id = sp.org_id
            WHERE sp.is_active = true
            ORDER BY sp.org_id, sp.display_name
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip},
    )).mappings().all()

    return {
        "items": [
            {
                "id":              str(r["id"]),
                "staff_code":      r["staff_code"],
                "display_name":    r["display_name"],
                "position":        r["position"],
                "department":      r["department"],
                "branch_name":     r["branch_name"],
                "employment_type": r["employment_type"],
                "is_verified":     r["is_verified"],
                "org_id":          str(r["org_id"]),
                "org_name":        r["org_name"],
            }
            for r in rows
        ],
        "count": len(rows),
    }
