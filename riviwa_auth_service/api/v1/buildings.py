"""
api/v1/buildings.py — Building structure CRUD: Buildings, Floors, Zones, POIs.
═══════════════════════════════════════════════════════════════════════════════
Hierarchy:
  OrgBranch → OrgBuilding → OrgFloor → OrgZone → OrgPointOfInterest

Barometric floor detection:
  POST /orgs/{org_id}/buildings/{bid}/floors/{fid}/calibrate
  Org admin stands on a floor and submits their phone's barometric pressure
  reading. Server stores calibrated_pressure_hpa on OrgFloor. At feedback
  submission time, feedback_service compares the user's pressure to each
  floor's calibrated value and picks the nearest match.

Emergency routing:
  POIs with is_emergency_point=True are triage counters, nurse stations,
  first-aid points, and emergency exits. The AI uses nearest_emergency_poi_id
  to direct users in distress to the closest help point.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from db.session import get_async_session as get_db

log = structlog.get_logger(__name__)
router = APIRouter(tags=["Building Structure"])


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class PolygonPoint(BaseModel):
    lat:   float = Field(ge=-90,  le=90)
    lng:   float = Field(ge=-180, le=180)
    label: Optional[str] = Field(default=None, max_length=50)


class CreateBuildingRequest(BaseModel):
    branch_id:             Optional[uuid.UUID] = None
    name:                  str                 = Field(min_length=1, max_length=200)
    code:                  Optional[str]       = Field(default=None, max_length=50)
    description:           Optional[str]       = None
    gps_lat:               Optional[float]     = Field(default=None, ge=-90, le=90)
    gps_lng:               Optional[float]     = Field(default=None, ge=-180, le=180)
    boundary_polygon:      Optional[List[PolygonPoint]] = None
    ground_altitude_m:     Optional[float]     = None
    ground_reference_hpa:  Optional[float]     = None
    reference_station_id:  Optional[str]       = Field(default=None, max_length=100)
    total_floors:          Optional[int]        = None
    accessibility_notes:   Optional[str]        = None


class UpdateBuildingRequest(BaseModel):
    name:                  Optional[str]       = Field(default=None, max_length=200)
    code:                  Optional[str]       = Field(default=None, max_length=50)
    description:           Optional[str]       = None
    gps_lat:               Optional[float]     = Field(default=None, ge=-90, le=90)
    gps_lng:               Optional[float]     = Field(default=None, ge=-180, le=180)
    boundary_polygon:      Optional[List[PolygonPoint]] = None
    ground_altitude_m:     Optional[float]     = None
    ground_reference_hpa:  Optional[float]     = None
    reference_station_id:  Optional[str]       = Field(default=None, max_length=100)
    total_floors:          Optional[int]        = None
    accessibility_notes:   Optional[str]        = None
    is_active:             Optional[bool]       = None


class CalibrateGroundRequest(BaseModel):
    pressure_hpa:    float  = Field(..., description="Barometric pressure at ground floor entrance (hPa)")
    altitude_m:      Optional[float] = Field(default=None, description="GPS altitude at entrance (metres)")


class CreateFloorRequest(BaseModel):
    floor_number:   int   = Field(..., description="-2=B2, -1=B1, 0=Ground, 1=First …")
    floor_name:     str   = Field(min_length=1, max_length=200)
    floor_height_m:   Optional[float] = None
    ceiling_height_m: Optional[float] = None
    floor_plan_url:   Optional[str]   = None


class UpdateFloorRequest(BaseModel):
    floor_name:       Optional[str]   = Field(default=None, max_length=200)
    floor_height_m:   Optional[float] = None
    ceiling_height_m: Optional[float] = None
    floor_plan_url:   Optional[str]   = None
    is_active:        Optional[bool]  = None


class CalibrateFloorRequest(BaseModel):
    pressure_hpa: float = Field(..., description="Barometric pressure measured while standing on this floor (hPa)")


class CreateZoneRequest(BaseModel):
    name:             str             = Field(min_length=1, max_length=200)
    code:             Optional[str]   = Field(default=None, max_length=50)
    zone_type:        str             = Field(min_length=1, max_length=50)
    boundary_polygon: Optional[List[PolygonPoint]] = None
    department_id:    Optional[uuid.UUID] = None


class UpdateZoneRequest(BaseModel):
    name:             Optional[str]   = Field(default=None, max_length=200)
    code:             Optional[str]   = Field(default=None, max_length=50)
    zone_type:        Optional[str]   = Field(default=None, max_length=50)
    boundary_polygon: Optional[List[PolygonPoint]] = None
    department_id:    Optional[uuid.UUID] = None
    is_active:        Optional[bool]  = None


class CreatePOIRequest(BaseModel):
    zone_id:                  Optional[uuid.UUID] = None
    name:                     str                 = Field(min_length=1, max_length=300)
    code:                     Optional[str]       = Field(default=None, max_length=100)
    poi_type:                 str                 = Field(min_length=1, max_length=50)
    gps_lat:                  Optional[float]     = Field(default=None, ge=-90, le=90)
    gps_lng:                  Optional[float]     = Field(default=None, ge=-180, le=180)
    gps_accuracy_radius_m:    Optional[int]       = Field(default=None, ge=1)
    boundary_polygon:         Optional[List[PolygonPoint]] = None
    department_id:            Optional[uuid.UUID] = None
    service_id:               Optional[uuid.UUID] = None
    staff_assigned_user_id:   Optional[uuid.UUID] = None
    is_emergency_point:       bool                = False
    nearest_emergency_poi_id: Optional[uuid.UUID] = None
    connections_to:           Optional[List[str]] = None
    qr_code_id:               Optional[uuid.UUID] = None
    accessibility_notes:      Optional[str]       = None


class UpdatePOIRequest(BaseModel):
    zone_id:                  Optional[uuid.UUID] = None
    name:                     Optional[str]       = Field(default=None, max_length=300)
    code:                     Optional[str]       = Field(default=None, max_length=100)
    poi_type:                 Optional[str]       = Field(default=None, max_length=50)
    gps_lat:                  Optional[float]     = Field(default=None, ge=-90, le=90)
    gps_lng:                  Optional[float]     = Field(default=None, ge=-180, le=180)
    gps_accuracy_radius_m:    Optional[int]       = Field(default=None, ge=1)
    boundary_polygon:         Optional[List[PolygonPoint]] = None
    department_id:            Optional[uuid.UUID] = None
    service_id:               Optional[uuid.UUID] = None
    staff_assigned_user_id:   Optional[uuid.UUID] = None
    is_emergency_point:       Optional[bool]      = None
    nearest_emergency_poi_id: Optional[uuid.UUID] = None
    connections_to:           Optional[List[str]] = None
    qr_code_id:               Optional[uuid.UUID] = None
    accessibility_notes:      Optional[str]       = None
    is_active:                Optional[bool]      = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _require_org_admin(org_id: uuid.UUID, user: dict, db: AsyncSession) -> None:
    row = (await db.execute(
        text("""
            SELECT org_role FROM organisation_members
            WHERE organisation_id = :org_id AND user_id = :uid AND status = 'ACTIVE'
        """),
        {"org_id": str(org_id), "uid": str(user["id"])},
    )).mappings().first()
    if not row or row["org_role"] not in ("OWNER", "ADMIN", "MANAGER"):
        raise HTTPException(status_code=403, detail="Org admin access required.")


def _poly_to_json(poly: Optional[List[PolygonPoint]]):
    if not poly:
        return None
    return [{"lat": p.lat, "lng": p.lng, "label": p.label} for p in poly]


# ═════════════════════════════════════════════════════════════════════════════
# BUILDINGS
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/buildings",
    status_code=status.HTTP_201_CREATED,
    summary="Create a building within an org/branch",
)
async def create_building(
    org_id: uuid.UUID,
    body:   CreateBuildingRequest,
    user:   dict          = Depends(get_current_user),
    db:     AsyncSession  = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    row = (await db.execute(
        text("""
            INSERT INTO org_buildings (
                id, organisation_id, branch_id, name, code, description,
                gps_lat, gps_lng, boundary_polygon, ground_altitude_m,
                ground_reference_hpa, reference_station_id, total_floors,
                accessibility_notes, is_active, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :org_id, :branch_id, :name, :code, :description,
                :gps_lat, :gps_lng, :boundary_polygon::jsonb, :ground_altitude_m,
                :ground_reference_hpa, :reference_station_id, :total_floors,
                :accessibility_notes, true, now(), now()
            ) RETURNING *
        """),
        {
            "org_id": str(org_id),
            "branch_id": str(body.branch_id) if body.branch_id else None,
            "name": body.name,
            "code": body.code,
            "description": body.description,
            "gps_lat": body.gps_lat,
            "gps_lng": body.gps_lng,
            "boundary_polygon": __import__("json").dumps(_poly_to_json(body.boundary_polygon)) if body.boundary_polygon else None,
            "ground_altitude_m": body.ground_altitude_m,
            "ground_reference_hpa": body.ground_reference_hpa,
            "reference_station_id": body.reference_station_id,
            "total_floors": body.total_floors,
            "accessibility_notes": body.accessibility_notes,
        },
    )).mappings().first()
    await db.commit()
    return dict(row)


@router.get(
    "/orgs/{org_id}/buildings",
    summary="List buildings for an org",
)
async def list_buildings(
    org_id:    uuid.UUID,
    branch_id: Optional[uuid.UUID] = Query(default=None),
    user:      dict         = Depends(get_current_user),
    db:        AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    clause = "AND branch_id = :branch_id" if branch_id else ""
    params: dict = {"org_id": str(org_id)}
    if branch_id:
        params["branch_id"] = str(branch_id)
    rows = (await db.execute(
        text(f"""
            SELECT * FROM org_buildings
            WHERE organisation_id = :org_id {clause}
            ORDER BY name
        """),
        params,
    )).mappings().all()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.get("/orgs/{org_id}/buildings/{building_id}", summary="Get a single building")
async def get_building(
    org_id: uuid.UUID, building_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    row = (await db.execute(
        text("SELECT * FROM org_buildings WHERE id = :id AND organisation_id = :org_id"),
        {"id": str(building_id), "org_id": str(org_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Building not found.")
    return dict(row)


@router.patch("/orgs/{org_id}/buildings/{building_id}", summary="Update a building")
async def update_building(
    org_id: uuid.UUID, building_id: uuid.UUID,
    body: UpdateBuildingRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    updates = body.model_dump(exclude_none=True)
    if "boundary_polygon" in updates:
        import json
        updates["boundary_polygon"] = json.dumps(_poly_to_json(body.boundary_polygon))
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(building_id)
    updates["org_id"] = str(org_id)
    row = (await db.execute(
        text(f"""
            UPDATE org_buildings SET {set_clause}, updated_at = now()
            WHERE id = :id AND organisation_id = :org_id RETURNING *
        """),
        updates,
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Building not found.")
    await db.commit()
    return dict(row)


@router.post(
    "/orgs/{org_id}/buildings/{building_id}/calibrate-ground",
    summary="Set ground floor barometric reference pressure",
)
async def calibrate_building_ground(
    org_id: uuid.UUID, building_id: uuid.UUID,
    body: CalibrateGroundRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin stands at the building's main entrance (ground floor) and submits
    the phone barometer reading. This establishes the weather-adjusted baseline
    for floor detection. Should be re-calibrated whenever weather changes significantly
    (or automatically via a reference_station_id IoT device).
    """
    await _require_org_admin(org_id, user, db)
    row = (await db.execute(
        text("""
            UPDATE org_buildings
            SET ground_reference_hpa = :hpa,
                ground_altitude_m    = :alt,
                reference_taken_at   = now(),
                updated_at           = now()
            WHERE id = :id AND organisation_id = :org_id
            RETURNING id, name, ground_reference_hpa, ground_altitude_m, reference_taken_at
        """),
        {"hpa": body.pressure_hpa, "alt": body.altitude_m,
         "id": str(building_id), "org_id": str(org_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Building not found.")
    await db.commit()
    log.info("building.ground_calibrated", building=str(building_id), hpa=body.pressure_hpa)
    return dict(row)


@router.delete("/orgs/{org_id}/buildings/{building_id}", status_code=204, summary="Deactivate a building")
async def deactivate_building(
    org_id: uuid.UUID, building_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    await _require_org_admin(org_id, user, db)
    await db.execute(
        text("UPDATE org_buildings SET is_active = false, updated_at = now() WHERE id = :id AND organisation_id = :org_id"),
        {"id": str(building_id), "org_id": str(org_id)},
    )
    await db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# FLOORS
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/buildings/{building_id}/floors",
    status_code=201,
    summary="Add a floor to a building",
)
async def create_floor(
    org_id: uuid.UUID, building_id: uuid.UUID,
    body: CreateFloorRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    row = (await db.execute(
        text("""
            INSERT INTO org_floors (
                id, building_id, organisation_id, floor_number, floor_name,
                floor_height_m, ceiling_height_m, floor_plan_url,
                is_active, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :building_id, :org_id, :floor_number, :floor_name,
                :floor_height_m, :ceiling_height_m, :floor_plan_url,
                true, now(), now()
            ) RETURNING *
        """),
        {
            "building_id": str(building_id), "org_id": str(org_id),
            "floor_number": body.floor_number, "floor_name": body.floor_name,
            "floor_height_m": body.floor_height_m, "ceiling_height_m": body.ceiling_height_m,
            "floor_plan_url": body.floor_plan_url,
        },
    )).mappings().first()
    await db.commit()
    return dict(row)


@router.get(
    "/orgs/{org_id}/buildings/{building_id}/floors",
    summary="List floors in a building",
)
async def list_floors(
    org_id: uuid.UUID, building_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    rows = (await db.execute(
        text("""
            SELECT * FROM org_floors
            WHERE building_id = :building_id AND organisation_id = :org_id AND is_active = true
            ORDER BY floor_number
        """),
        {"building_id": str(building_id), "org_id": str(org_id)},
    )).mappings().all()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.patch(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}",
    summary="Update a floor",
)
async def update_floor(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    body: UpdateFloorRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates.update({"id": str(floor_id), "building_id": str(building_id), "org_id": str(org_id)})
    row = (await db.execute(
        text(f"""
            UPDATE org_floors SET {set_clause}, updated_at = now()
            WHERE id = :id AND building_id = :building_id AND organisation_id = :org_id
            RETURNING *
        """),
        updates,
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Floor not found.")
    await db.commit()
    return dict(row)


@router.post(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/calibrate",
    summary="Calibrate barometric pressure for a floor",
)
async def calibrate_floor(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    body: CalibrateFloorRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin stands on this floor and submits the phone's barometric pressure reading.
    The server stores calibrated_pressure_hpa on the floor record.

    At feedback submission time, feedback_service compares the user's live pressure
    to ALL calibrated floors in the building and selects the closest match.

    Accuracy note: Re-calibrate all floors on the same day to avoid weather drift
    between floor readings. The building's ground_reference_hpa is also updated
    by calibrate-ground and used as drift correction.
    """
    await _require_org_admin(org_id, user, db)
    row = (await db.execute(
        text("""
            UPDATE org_floors
            SET calibrated_pressure_hpa = :hpa, calibrated_at = now(), updated_at = now()
            WHERE id = :id AND building_id = :building_id AND organisation_id = :org_id
            RETURNING id, floor_number, floor_name, calibrated_pressure_hpa, calibrated_at
        """),
        {"hpa": body.pressure_hpa, "id": str(floor_id),
         "building_id": str(building_id), "org_id": str(org_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Floor not found.")
    await db.commit()
    log.info("floor.calibrated",
             floor=str(floor_id), floor_number=row["floor_number"], hpa=body.pressure_hpa)
    return dict(row)


@router.delete(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}",
    status_code=204,
    summary="Deactivate a floor",
)
async def deactivate_floor(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    await _require_org_admin(org_id, user, db)
    await db.execute(
        text("""
            UPDATE org_floors SET is_active = false, updated_at = now()
            WHERE id = :id AND building_id = :building_id AND organisation_id = :org_id
        """),
        {"id": str(floor_id), "building_id": str(building_id), "org_id": str(org_id)},
    )
    await db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# ZONES
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/zones",
    status_code=201,
    summary="Create a zone within a floor",
)
async def create_zone(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    body: CreateZoneRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    import json
    row = (await db.execute(
        text("""
            INSERT INTO org_zones (
                id, floor_id, organisation_id, name, code, zone_type,
                boundary_polygon, department_id, is_active, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :floor_id, :org_id, :name, :code, :zone_type,
                :boundary_polygon::jsonb, :department_id, true, now(), now()
            ) RETURNING *
        """),
        {
            "floor_id": str(floor_id), "org_id": str(org_id),
            "name": body.name, "code": body.code, "zone_type": body.zone_type,
            "boundary_polygon": json.dumps(_poly_to_json(body.boundary_polygon)) if body.boundary_polygon else None,
            "department_id": str(body.department_id) if body.department_id else None,
        },
    )).mappings().first()
    await db.commit()
    return dict(row)


@router.get(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/zones",
    summary="List zones on a floor",
)
async def list_zones(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    rows = (await db.execute(
        text("""
            SELECT * FROM org_zones
            WHERE floor_id = :floor_id AND organisation_id = :org_id AND is_active = true
            ORDER BY name
        """),
        {"floor_id": str(floor_id), "org_id": str(org_id)},
    )).mappings().all()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.patch(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/zones/{zone_id}",
    summary="Update a zone",
)
async def update_zone(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID, zone_id: uuid.UUID,
    body: UpdateZoneRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    import json
    updates = body.model_dump(exclude_none=True)
    if "boundary_polygon" in updates:
        updates["boundary_polygon"] = json.dumps(_poly_to_json(body.boundary_polygon))
    if "department_id" in updates and updates["department_id"]:
        updates["department_id"] = str(updates["department_id"])
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates.update({"id": str(zone_id), "floor_id": str(floor_id), "org_id": str(org_id)})
    row = (await db.execute(
        text(f"""
            UPDATE org_zones SET {set_clause}, updated_at = now()
            WHERE id = :id AND floor_id = :floor_id AND organisation_id = :org_id
            RETURNING *
        """),
        updates,
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found.")
    await db.commit()
    return dict(row)


@router.delete(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/zones/{zone_id}",
    status_code=204,
    summary="Deactivate a zone",
)
async def deactivate_zone(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID, zone_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    await _require_org_admin(org_id, user, db)
    await db.execute(
        text("UPDATE org_zones SET is_active = false, updated_at = now() WHERE id = :id AND organisation_id = :org_id"),
        {"id": str(zone_id), "org_id": str(org_id)},
    )
    await db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# POINTS OF INTEREST
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/pois",
    status_code=201,
    summary="Create a Point of Interest on a floor",
)
async def create_poi(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    body: CreatePOIRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    import json
    row = (await db.execute(
        text("""
            INSERT INTO org_points_of_interest (
                id, floor_id, zone_id, organisation_id, name, code, poi_type,
                gps_lat, gps_lng, gps_accuracy_radius_m, boundary_polygon,
                department_id, service_id, staff_assigned_user_id,
                is_emergency_point, nearest_emergency_poi_id,
                connections_to, qr_code_id, accessibility_notes,
                is_active, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :floor_id, :zone_id, :org_id, :name, :code, :poi_type,
                :gps_lat, :gps_lng, :gps_accuracy_radius_m, :boundary_polygon::jsonb,
                :department_id, :service_id, :staff_assigned_user_id,
                :is_emergency_point, :nearest_emergency_poi_id,
                :connections_to::jsonb, :qr_code_id, :accessibility_notes,
                true, now(), now()
            ) RETURNING *
        """),
        {
            "floor_id": str(floor_id),
            "zone_id": str(body.zone_id) if body.zone_id else None,
            "org_id": str(org_id),
            "name": body.name, "code": body.code, "poi_type": body.poi_type,
            "gps_lat": body.gps_lat, "gps_lng": body.gps_lng,
            "gps_accuracy_radius_m": body.gps_accuracy_radius_m,
            "boundary_polygon": json.dumps(_poly_to_json(body.boundary_polygon)) if body.boundary_polygon else None,
            "department_id": str(body.department_id) if body.department_id else None,
            "service_id": str(body.service_id) if body.service_id else None,
            "staff_assigned_user_id": str(body.staff_assigned_user_id) if body.staff_assigned_user_id else None,
            "is_emergency_point": body.is_emergency_point,
            "nearest_emergency_poi_id": str(body.nearest_emergency_poi_id) if body.nearest_emergency_poi_id else None,
            "connections_to": json.dumps(body.connections_to) if body.connections_to else None,
            "qr_code_id": str(body.qr_code_id) if body.qr_code_id else None,
            "accessibility_notes": body.accessibility_notes,
        },
    )).mappings().first()
    await db.commit()
    log.info("poi.created", poi=str(row["id"]), floor=str(floor_id), poi_type=body.poi_type)
    return dict(row)


@router.get(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/pois",
    summary="List POIs on a floor",
)
async def list_pois(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID,
    zone_id:            Optional[uuid.UUID] = Query(default=None),
    poi_type:           Optional[str]       = Query(default=None),
    emergency_only:     bool                = Query(default=False),
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    clauses = ["floor_id = :floor_id", "organisation_id = :org_id", "is_active = true"]
    params: dict = {"floor_id": str(floor_id), "org_id": str(org_id)}
    if zone_id:
        clauses.append("zone_id = :zone_id")
        params["zone_id"] = str(zone_id)
    if poi_type:
        clauses.append("poi_type = :poi_type")
        params["poi_type"] = poi_type
    if emergency_only:
        clauses.append("is_emergency_point = true")
    where = " AND ".join(clauses)
    rows = (await db.execute(
        text(f"SELECT * FROM org_points_of_interest WHERE {where} ORDER BY name"),
        params,
    )).mappings().all()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.get(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/pois/{poi_id}",
    summary="Get a single POI",
)
async def get_poi(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID, poi_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    row = (await db.execute(
        text("SELECT * FROM org_points_of_interest WHERE id = :id AND floor_id = :floor_id AND organisation_id = :org_id"),
        {"id": str(poi_id), "floor_id": str(floor_id), "org_id": str(org_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="POI not found.")
    return dict(row)


@router.patch(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/pois/{poi_id}",
    summary="Update a POI",
)
async def update_poi(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID, poi_id: uuid.UUID,
    body: UpdatePOIRequest,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await _require_org_admin(org_id, user, db)
    import json
    updates = body.model_dump(exclude_none=True)
    for uuid_field in ("zone_id", "department_id", "service_id", "staff_assigned_user_id",
                       "nearest_emergency_poi_id", "qr_code_id"):
        if uuid_field in updates and updates[uuid_field]:
            updates[uuid_field] = str(updates[uuid_field])
    if "boundary_polygon" in updates:
        updates["boundary_polygon"] = json.dumps(_poly_to_json(body.boundary_polygon))
    if "connections_to" in updates:
        updates["connections_to"] = json.dumps(updates["connections_to"])
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates.update({"id": str(poi_id), "floor_id": str(floor_id), "org_id": str(org_id)})
    row = (await db.execute(
        text(f"""
            UPDATE org_points_of_interest SET {set_clause}, updated_at = now()
            WHERE id = :id AND floor_id = :floor_id AND organisation_id = :org_id
            RETURNING *
        """),
        updates,
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="POI not found.")
    await db.commit()
    return dict(row)


@router.delete(
    "/orgs/{org_id}/buildings/{building_id}/floors/{floor_id}/pois/{poi_id}",
    status_code=204,
    summary="Deactivate a POI",
)
async def deactivate_poi(
    org_id: uuid.UUID, building_id: uuid.UUID, floor_id: uuid.UUID, poi_id: uuid.UUID,
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    await _require_org_admin(org_id, user, db)
    await db.execute(
        text("""
            UPDATE org_points_of_interest SET is_active = false, updated_at = now()
            WHERE id = :id AND floor_id = :floor_id AND organisation_id = :org_id
        """),
        {"id": str(poi_id), "floor_id": str(floor_id), "org_id": str(org_id)},
    )
    await db.commit()
