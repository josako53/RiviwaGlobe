"""api/v1/projects.py — HTTP orchestration only"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from core.dependencies import DbDep, StaffDep
from models.project import ProjectStatus
from services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


def _svc(db: DbDep) -> ProjectService:
    return ProjectService(db=db)


def _project_out(p) -> dict:
    return {
        "id":              str(p.id),
        "organisation_id": str(p.organisation_id),
        "branch_id":       str(p.branch_id) if p.branch_id else None,
        "name":            p.name,
        "code":            p.code,
        "slug":            p.slug,
        "status":          p.status,
        "category":        p.category,
        "sector":          p.sector,
        "country_code":    p.country_code,
        "region":          p.region,
        "primary_lga":     p.primary_lga,
        "accepts_grievances":  p.accepts_grievances,
        "accepts_suggestions": p.accepts_suggestions,
        "accepts_applause":    p.accepts_applause,
        "published_at":    p.published_at.isoformat() if p.published_at else None,
        "synced_at":       p.synced_at.isoformat(),
    }


@router.get("", summary="List synced projects")
async def list_projects(
    db:     DbDep,
    _:      StaffDep,
    status: Optional[ProjectStatus] = Query(default=None),
    org_id: Optional[uuid.UUID]     = Query(default=None),
    lga:    Optional[str]           = Query(default=None),
    skip:   int                     = Query(default=0, ge=0),
    limit:  int                     = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db).list(status=status, org_id=org_id, lga=lga, skip=skip, limit=limit)
    return {"items": [_project_out(p) for p in items], "count": len(items)}


@router.get("/{project_id}", summary="Project detail with engagement counts")
async def get_project(project_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    project, counts = await _svc(db).get_with_counts(project_id)
    return {**_project_out(project), "counts": counts}
