# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000
# FILE     :  api/v1/org_structure.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/org_structure.py
═══════════════════════════════════════════════════════════════════════════════
Org structural data: organigram (GRAM/leadership), operating hours,
and geographic boundary polygons.

Route inventory
────────────────
  Organigram / Leadership (GRAM)
    POST   /orgs/{org_id}/leadership                            [ADMIN+]
    GET    /orgs/{org_id}/leadership                            [MEMBER+]
    GET    /orgs/{org_id}/leadership/tree                       [MEMBER+]
    PATCH  /orgs/{org_id}/leadership/{role_id}                  [ADMIN+]
    DELETE /orgs/{org_id}/leadership/{role_id}                  [ADMIN+]
    GET    /orgs/{org_id}/branches/{branch_id}/leadership       [MEMBER+]

    Public (no auth, is_public=True only)
    GET    /public/orgs/{org_id}/organigram

  Operating Hours
    GET    /orgs/{org_id}/operating-hours                       [MEMBER+]
    PUT    /orgs/{org_id}/operating-hours                       [ADMIN+]  upsert full week
    PATCH  /orgs/{org_id}/operating-hours/{day}                 [ADMIN+]  single-day patch
    DELETE /orgs/{org_id}/operating-hours/{day}                 [ADMIN+]
    GET    /orgs/{org_id}/branches/{branch_id}/operating-hours  [MEMBER+]
    PUT    /orgs/{org_id}/branches/{branch_id}/operating-hours  [ADMIN+]

  Geographic Boundaries
    POST   /orgs/{org_id}/geo-boundaries                        [ADMIN+]
    GET    /orgs/{org_id}/geo-boundaries                        [MEMBER+]
    PATCH  /orgs/{org_id}/geo-boundaries/{boundary_id}          [ADMIN+]
    DELETE /orgs/{org_id}/geo-boundaries/{boundary_id}          [ADMIN+]
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import DbDep
from core.dependencies import require_org_role
from models.organisation import OrgMemberRole
from models.org_structure import (
    DayOfWeek,
    GeoBoundaryType,
    LeadershipScope,
    OrgGeoBoundary,
    OrgLeadershipRole,
    OrgOperatingHours,
)

log = structlog.get_logger(__name__)

router = APIRouter(tags=["Org Structure"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _role_out(r: OrgLeadershipRole) -> dict:
    return {
        "id":             str(r.id),
        "org_id":         str(r.org_id),
        "branch_id":      str(r.branch_id) if r.branch_id else None,
        "user_id":        str(r.user_id)   if r.user_id   else None,
        "full_name":      r.full_name,
        "photo_url":      r.photo_url,
        "role_title":     r.role_title,
        "scope":          r.scope,
        "duties":         r.duties,
        "department":     r.department,
        "phone":          r.phone,
        "email":          r.email,
        "parent_role_id": str(r.parent_role_id) if r.parent_role_id else None,
        "level":          r.level,
        "sort_order":     r.sort_order,
        "is_public":      r.is_public,
        "is_active":      r.is_active,
        "started_on":     r.started_on.isoformat() if r.started_on else None,
        "ended_on":       r.ended_on.isoformat()   if r.ended_on   else None,
        "created_at":     r.created_at.isoformat(),
        "updated_at":     r.updated_at.isoformat(),
    }


def _hours_out(h: OrgOperatingHours) -> dict:
    return {
        "id":          str(h.id),
        "org_id":      str(h.org_id)     if h.org_id     else None,
        "branch_id":   str(h.branch_id)  if h.branch_id  else None,
        "day_of_week": h.day_of_week,
        "is_open":     h.is_open,
        "open_time":   h.open_time.strftime("%H:%M")  if h.open_time  else None,
        "close_time":  h.close_time.strftime("%H:%M") if h.close_time else None,
        "break_start": h.break_start.strftime("%H:%M") if h.break_start else None,
        "break_end":   h.break_end.strftime("%H:%M")   if h.break_end  else None,
        "timezone":    h.timezone,
        "notes":       h.notes,
        "updated_at":  h.updated_at.isoformat(),
    }


def _boundary_out(b: OrgGeoBoundary) -> dict:
    return {
        "id":            str(b.id),
        "org_id":        str(b.org_id)    if b.org_id    else None,
        "branch_id":     str(b.branch_id) if b.branch_id else None,
        "boundary_type": b.boundary_type,
        "name":          b.name,
        "description":   b.description,
        "geojson":       b.geojson,
        "bbox_min_lat":  b.bbox_min_lat,
        "bbox_max_lat":  b.bbox_max_lat,
        "bbox_min_lng":  b.bbox_min_lng,
        "bbox_max_lng":  b.bbox_max_lng,
        "is_active":     b.is_active,
        "created_at":    b.created_at.isoformat(),
        "updated_at":    b.updated_at.isoformat(),
    }


def _build_tree(roles: list[OrgLeadershipRole]) -> list[dict]:
    """Build nested organigram tree from a flat list."""
    by_id: dict[uuid.UUID, dict] = {}
    for r in roles:
        by_id[r.id] = {**_role_out(r), "children": []}

    roots: list[dict] = []
    for r in roles:
        node = by_id[r.id]
        if r.parent_role_id and r.parent_role_id in by_id:
            by_id[r.parent_role_id]["children"].append(node)
        else:
            roots.append(node)

    roots.sort(key=lambda x: (x["level"], x["sort_order"]))
    return roots


def _parse_time(t: Optional[str]) -> Optional[time]:
    if not t:
        return None
    try:
        h, m = t.split(":")
        return time(int(h), int(m))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid time format '{t}' — use HH:MM",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────────────────────

class CreateLeadershipRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    branch_id:      Optional[uuid.UUID]     = None
    user_id:        Optional[uuid.UUID]     = None
    full_name:      str                     = Field(min_length=1, max_length=200)
    photo_url:      Optional[str]           = Field(default=None, max_length=1024)
    role_title:     str                     = Field(min_length=1, max_length=200)
    scope:          LeadershipScope         = LeadershipScope.MANAGEMENT
    duties:         Optional[str]           = None
    department:     Optional[str]           = Field(default=None, max_length=200)
    phone:          Optional[str]           = Field(default=None, max_length=30)
    email:          Optional[str]           = Field(default=None, max_length=255)
    parent_role_id: Optional[uuid.UUID]     = None
    level:          int                     = Field(default=1, ge=1)
    sort_order:     int                     = 0
    is_public:      bool                    = True
    started_on:     Optional[datetime]      = None
    ended_on:       Optional[datetime]      = None


class UpdateLeadershipRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    branch_id:      Optional[uuid.UUID]     = None
    user_id:        Optional[uuid.UUID]     = None
    full_name:      Optional[str]           = Field(default=None, max_length=200)
    photo_url:      Optional[str]           = None
    role_title:     Optional[str]           = Field(default=None, max_length=200)
    scope:          Optional[LeadershipScope] = None
    duties:         Optional[str]           = None
    department:     Optional[str]           = None
    phone:          Optional[str]           = None
    email:          Optional[str]           = None
    parent_role_id: Optional[uuid.UUID]     = None
    level:          Optional[int]           = Field(default=None, ge=1)
    sort_order:     Optional[int]           = None
    is_public:      Optional[bool]          = None
    is_active:      Optional[bool]          = None
    started_on:     Optional[datetime]      = None
    ended_on:       Optional[datetime]      = None


class HoursEntryRequest(BaseModel):
    """One day's hours — used in both upsert-week and single-day PATCH."""
    model_config = ConfigDict(str_strip_whitespace=True)
    day_of_week: DayOfWeek
    is_open:     bool       = True
    open_time:   Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    close_time:  Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    break_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    break_end:   Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone:    str           = "Africa/Dar_es_Salaam"
    notes:       Optional[str] = None


class UpsertWeekRequest(BaseModel):
    """Full 7-day schedule — PUT replaces the entire week."""
    days: list[HoursEntryRequest] = Field(min_length=1, max_length=7)


class PatchDayRequest(BaseModel):
    """Partial update for a single day — PATCH."""
    model_config = ConfigDict(str_strip_whitespace=True)
    is_open:     Optional[bool] = None
    open_time:   Optional[str]  = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    close_time:  Optional[str]  = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    break_start: Optional[str]  = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    break_end:   Optional[str]  = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone:    Optional[str]  = None
    notes:       Optional[str]  = None


class CreateGeoBoundaryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    branch_id:     Optional[uuid.UUID]   = None
    boundary_type: GeoBoundaryType       = GeoBoundaryType.SERVICE_AREA
    name:          str                   = Field(min_length=1, max_length=300)
    description:   Optional[str]         = None
    geojson:       dict                  = Field(description="GeoJSON Polygon or MultiPolygon")
    bbox_min_lat:  Optional[float]       = None
    bbox_max_lat:  Optional[float]       = None
    bbox_min_lng:  Optional[float]       = None
    bbox_max_lng:  Optional[float]       = None


class UpdateGeoBoundaryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    boundary_type: Optional[GeoBoundaryType] = None
    name:          Optional[str]             = Field(default=None, max_length=300)
    description:   Optional[str]             = None
    geojson:       Optional[dict]            = None
    bbox_min_lat:  Optional[float]           = None
    bbox_max_lat:  Optional[float]           = None
    bbox_min_lng:  Optional[float]           = None
    bbox_max_lng:  Optional[float]           = None
    is_active:     Optional[bool]            = None


# ═════════════════════════════════════════════════════════════════════════════
# ORGANIGRAM / LEADERSHIP  endpoints
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/leadership",
    status_code=status.HTTP_201_CREATED,
    summary="Add a person/role to the org organigram [ADMIN+]",
)
async def create_leadership_role(
    org_id: uuid.UUID,
    body:   CreateLeadershipRequest,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    role = OrgLeadershipRole(
        org_id=org_id,
        **body.model_dump(exclude_none=True),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return _role_out(role)


@router.get(
    "/orgs/{org_id}/leadership",
    summary="List org leadership roles (flat) [MEMBER+]",
)
async def list_leadership_roles(
    org_id:      uuid.UUID,
    db:          DbDep,
    scope:       Optional[LeadershipScope] = Query(default=None),
    branch_id:   Optional[uuid.UUID]       = Query(default=None),
    active_only: bool                      = Query(default=True),
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    q = select(OrgLeadershipRole).where(OrgLeadershipRole.org_id == org_id)
    if scope:
        q = q.where(OrgLeadershipRole.scope == scope)
    if branch_id:
        q = q.where(OrgLeadershipRole.branch_id == branch_id)
    if active_only:
        q = q.where(OrgLeadershipRole.is_active.is_(True))
    q = q.order_by(OrgLeadershipRole.level, OrgLeadershipRole.sort_order)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_role_out(r) for r in rows], "count": len(rows)}


@router.get(
    "/orgs/{org_id}/leadership/tree",
    summary="Get org organigram as a nested tree [MEMBER+]",
)
async def get_organigram_tree(
    org_id:      uuid.UUID,
    db:          DbDep,
    active_only: bool = Query(default=True),
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    q = select(OrgLeadershipRole).where(OrgLeadershipRole.org_id == org_id)
    if active_only:
        q = q.where(OrgLeadershipRole.is_active.is_(True))
    q = q.order_by(OrgLeadershipRole.level, OrgLeadershipRole.sort_order)
    rows = (await db.execute(q)).scalars().all()
    return {"tree": _build_tree(rows), "total": len(rows)}


@router.get(
    "/orgs/{org_id}/branches/{branch_id}/leadership",
    summary="List leadership roles scoped to a specific branch [MEMBER+]",
)
async def list_branch_leadership(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    db:        DbDep,
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    q = (
        select(OrgLeadershipRole)
        .where(OrgLeadershipRole.org_id == org_id)
        .where(OrgLeadershipRole.branch_id == branch_id)
        .where(OrgLeadershipRole.is_active.is_(True))
        .order_by(OrgLeadershipRole.level, OrgLeadershipRole.sort_order)
    )
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_role_out(r) for r in rows], "count": len(rows)}


@router.patch(
    "/orgs/{org_id}/leadership/{role_id}",
    summary="Update a leadership role [ADMIN+]",
)
async def update_leadership_role(
    org_id:  uuid.UUID,
    role_id: uuid.UUID,
    body:    UpdateLeadershipRequest,
    db:      DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = (await db.execute(
        select(OrgLeadershipRole)
        .where(OrgLeadershipRole.id == role_id)
        .where(OrgLeadershipRole.org_id == org_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Leadership role not found.")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(row, field, val)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return _role_out(row)


@router.delete(
    "/orgs/{org_id}/leadership/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a leadership role from the organigram [ADMIN+]",
)
async def delete_leadership_role(
    org_id:  uuid.UUID,
    role_id: uuid.UUID,
    db:      DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = (await db.execute(
        select(OrgLeadershipRole)
        .where(OrgLeadershipRole.id == role_id)
        .where(OrgLeadershipRole.org_id == org_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Leadership role not found.")
    await db.delete(row)
    await db.commit()
    return {"detail": "Leadership role removed."}


# ── Public organigram (no auth) ───────────────────────────────────────────────

@router.get(
    "/public/orgs/{org_id}/organigram",
    summary="Public org organigram — is_public roles only (no auth required)",
)
async def public_organigram(
    org_id: uuid.UUID,
    db:     DbDep,
) -> dict:
    q = (
        select(OrgLeadershipRole)
        .where(OrgLeadershipRole.org_id == org_id)
        .where(OrgLeadershipRole.is_public.is_(True))
        .where(OrgLeadershipRole.is_active.is_(True))
        .order_by(OrgLeadershipRole.level, OrgLeadershipRole.sort_order)
    )
    rows = (await db.execute(q)).scalars().all()
    return {"tree": _build_tree(rows), "total": len(rows)}


# ═════════════════════════════════════════════════════════════════════════════
# OPERATING HOURS  endpoints
# ═════════════════════════════════════════════════════════════════════════════

async def _get_hours(
    db: AsyncSession,
    *,
    org_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
) -> list[OrgOperatingHours]:
    q = select(OrgOperatingHours)
    if org_id and not branch_id:
        q = q.where(OrgOperatingHours.org_id == org_id).where(
            OrgOperatingHours.branch_id.is_(None)
        )
    elif branch_id:
        q = q.where(OrgOperatingHours.branch_id == branch_id)
    q = q.order_by(OrgOperatingHours.day_of_week)
    return (await db.execute(q)).scalars().all()


async def _upsert_hours(
    db: AsyncSession,
    days: list[HoursEntryRequest],
    *,
    org_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
) -> list[OrgOperatingHours]:
    # Delete existing rows for this scope
    del_q = delete(OrgOperatingHours)
    if org_id and not branch_id:
        del_q = del_q.where(OrgOperatingHours.org_id == org_id).where(
            OrgOperatingHours.branch_id.is_(None)
        )
    elif branch_id:
        del_q = del_q.where(OrgOperatingHours.branch_id == branch_id)
    await db.execute(del_q)

    rows = []
    for day in days:
        row = OrgOperatingHours(
            org_id=org_id,
            branch_id=branch_id,
            day_of_week=day.day_of_week,
            is_open=day.is_open,
            open_time=_parse_time(day.open_time),
            close_time=_parse_time(day.close_time),
            break_start=_parse_time(day.break_start),
            break_end=_parse_time(day.break_end),
            timezone=day.timezone,
            notes=day.notes,
        )
        db.add(row)
        rows.append(row)

    await db.commit()
    for r in rows:
        await db.refresh(r)
    return rows


@router.get(
    "/orgs/{org_id}/operating-hours",
    summary="Get org-wide operating hours schedule [MEMBER+]",
)
async def get_org_hours(
    org_id: uuid.UUID,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    rows = await _get_hours(db, org_id=org_id)
    return {"schedule": [_hours_out(h) for h in rows], "count": len(rows)}


@router.put(
    "/orgs/{org_id}/operating-hours",
    summary="Upsert full org-wide weekly schedule (replaces existing) [ADMIN+]",
)
async def upsert_org_hours(
    org_id: uuid.UUID,
    body:   UpsertWeekRequest,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    rows = await _upsert_hours(db, body.days, org_id=org_id)
    return {"schedule": [_hours_out(h) for h in rows], "count": len(rows)}


@router.patch(
    "/orgs/{org_id}/operating-hours/{day}",
    summary="Update a single day in the org schedule [ADMIN+]",
)
async def patch_org_day(
    org_id: uuid.UUID,
    day:    DayOfWeek,
    body:   PatchDayRequest,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = (await db.execute(
        select(OrgOperatingHours)
        .where(OrgOperatingHours.org_id == org_id)
        .where(OrgOperatingHours.branch_id.is_(None))
        .where(OrgOperatingHours.day_of_week == day)
    )).scalar_one_or_none()

    if not row:
        # Create on first PATCH if no row exists
        row = OrgOperatingHours(org_id=org_id, day_of_week=day, is_open=True,
                                timezone="Africa/Dar_es_Salaam")
        db.add(row)

    data = body.model_dump(exclude_unset=True)
    for field in ("open_time", "close_time", "break_start", "break_end"):
        if field in data:
            data[field] = _parse_time(data[field])
    for field, val in data.items():
        setattr(row, field, val)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return _hours_out(row)


@router.delete(
    "/orgs/{org_id}/operating-hours/{day}",
    status_code=status.HTTP_200_OK,
    summary="Remove a day from the org schedule [ADMIN+]",
)
async def delete_org_day(
    org_id: uuid.UUID,
    day:    DayOfWeek,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    await db.execute(
        delete(OrgOperatingHours)
        .where(OrgOperatingHours.org_id == org_id)
        .where(OrgOperatingHours.branch_id.is_(None))
        .where(OrgOperatingHours.day_of_week == day)
    )
    await db.commit()
    return {"detail": f"{day} removed from org schedule."}


@router.get(
    "/orgs/{org_id}/branches/{branch_id}/operating-hours",
    summary="Get branch-specific operating hours schedule [MEMBER+]",
)
async def get_branch_hours(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    db:        DbDep,
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    rows = await _get_hours(db, branch_id=branch_id)
    return {"schedule": [_hours_out(h) for h in rows], "count": len(rows)}


@router.put(
    "/orgs/{org_id}/branches/{branch_id}/operating-hours",
    summary="Upsert full branch weekly schedule (replaces existing) [ADMIN+]",
)
async def upsert_branch_hours(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    body:      UpsertWeekRequest,
    db:        DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    rows = await _upsert_hours(db, body.days, branch_id=branch_id)
    return {"schedule": [_hours_out(h) for h in rows], "count": len(rows)}


# ═════════════════════════════════════════════════════════════════════════════
# GEO BOUNDARIES  endpoints
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/geo-boundaries",
    status_code=status.HTTP_201_CREATED,
    summary="Add a geographic boundary to an org [ADMIN+]",
)
async def create_geo_boundary(
    org_id: uuid.UUID,
    body:   CreateGeoBoundaryRequest,
    db:     DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    boundary = OrgGeoBoundary(
        org_id=org_id,
        **body.model_dump(exclude_none=True),
    )
    db.add(boundary)
    await db.commit()
    await db.refresh(boundary)
    return _boundary_out(boundary)


@router.get(
    "/orgs/{org_id}/geo-boundaries",
    summary="List geographic boundaries for an org [MEMBER+]",
)
async def list_geo_boundaries(
    org_id:        uuid.UUID,
    db:            DbDep,
    boundary_type: Optional[GeoBoundaryType] = Query(default=None),
    branch_id:     Optional[uuid.UUID]       = Query(default=None),
    active_only:   bool                      = Query(default=True),
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    q = select(OrgGeoBoundary).where(OrgGeoBoundary.org_id == org_id)
    if boundary_type:
        q = q.where(OrgGeoBoundary.boundary_type == boundary_type)
    if branch_id:
        q = q.where(OrgGeoBoundary.branch_id == branch_id)
    if active_only:
        q = q.where(OrgGeoBoundary.is_active.is_(True))
    q = q.order_by(OrgGeoBoundary.boundary_type, OrgGeoBoundary.created_at)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_boundary_out(b) for b in rows], "count": len(rows)}


@router.patch(
    "/orgs/{org_id}/geo-boundaries/{boundary_id}",
    summary="Update a geographic boundary [ADMIN+]",
)
async def update_geo_boundary(
    org_id:      uuid.UUID,
    boundary_id: uuid.UUID,
    body:        UpdateGeoBoundaryRequest,
    db:          DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = (await db.execute(
        select(OrgGeoBoundary)
        .where(OrgGeoBoundary.id == boundary_id)
        .where(OrgGeoBoundary.org_id == org_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Geo boundary not found.")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(row, field, val)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return _boundary_out(row)


@router.delete(
    "/orgs/{org_id}/geo-boundaries/{boundary_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a geographic boundary [ADMIN+]",
)
async def delete_geo_boundary(
    org_id:      uuid.UUID,
    boundary_id: uuid.UUID,
    db:          DbDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = (await db.execute(
        select(OrgGeoBoundary)
        .where(OrgGeoBoundary.id == boundary_id)
        .where(OrgGeoBoundary.org_id == org_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Geo boundary not found.")
    await db.delete(row)
    await db.commit()
    return {"detail": "Geo boundary removed."}
