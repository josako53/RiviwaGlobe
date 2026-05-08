"""api/v1/internal.py — Internal and third-party API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from core.dependencies import ApiKeyDep, DbDep, InternalDep
from core.exceptions import StaffNotFoundError
from repositories.org_cache_repository import OrgCacheRepository
from repositories.staff_profile_repository import StaffProfileRepository
from schemas.staff_profile import StaffPublicOut

router = APIRouter(prefix="/api/v1/staff", tags=["Internal"])


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
