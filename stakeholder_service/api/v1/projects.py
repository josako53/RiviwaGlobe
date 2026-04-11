"""api/v1/projects.py — HTTP orchestration only"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from core.dependencies import DbDep, StaffDep
from models.project import ProjectStatus
from repositories.activity_repository import ActivityRepository
from repositories.stakeholder_repository import StakeholderRepository
from services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


def _svc(db: DbDep) -> ProjectService:
    return ProjectService(db=db)


def _stage_out(s) -> dict:
    return {
        "id":          str(s.id),
        "name":        s.name,
        "stage_order": s.stage_order,
        "status":      s.status,
        "description": s.description,
        "objectives":  s.objectives,
        "start_date":  s.start_date.isoformat() if s.start_date else None,
        "end_date":    s.end_date.isoformat() if s.end_date else None,
        "accepts_grievances":  s.accepts_grievances,
        "accepts_suggestions": s.accepts_suggestions,
        "accepts_applause":    s.accepts_applause,
    }


def _project_out(p, include_stages: bool = False) -> dict:
    out = {
        "id":              str(p.id),
        "organisation_id": str(p.organisation_id),
        "branch_id":       str(p.branch_id) if p.branch_id else None,
        "name":            p.name,
        "code":            p.code,
        "slug":            p.slug,
        "status":          p.status,
        "category":        p.category,
        "sector":          p.sector,
        "description":     p.description,
        "country_code":    p.country_code,
        "region":          p.region,
        "primary_lga":     p.primary_lga,
        "start_date":      p.start_date.isoformat() if p.start_date else None,
        "end_date":        p.end_date.isoformat() if p.end_date else None,
        "accepts_grievances":  p.accepts_grievances,
        "accepts_suggestions": p.accepts_suggestions,
        "accepts_applause":    p.accepts_applause,
        "published_at":    p.published_at.isoformat() if p.published_at else None,
        "synced_at":       p.synced_at.isoformat(),
    }
    if include_stages:
        out["stages"] = [_stage_out(s) for s in (p.stages or [])]
    return out


def _stakeholder_brief(s) -> dict:
    return {
        "id":               str(s.id),
        "stakeholder_type": s.stakeholder_type,
        "entity_type":      s.entity_type,
        "category":         s.category,
        "display_name":     s.display_name,
        "affectedness":     s.affectedness,
        "importance_rating": s.importance_rating,
        "lga":              s.lga,
        "ward":             s.ward,
        "is_vulnerable":    s.is_vulnerable,
        "language_preference": s.language_preference,
    }


def _activity_brief(a) -> dict:
    return {
        "id":            str(a.id),
        "stage_id":      str(a.stage_id) if a.stage_id else None,
        "stage":         a.stage,
        "activity_type": a.activity_type,
        "status":        a.status,
        "title":         a.title,
        "venue":         a.venue,
        "lga":           a.lga,
        "scheduled_at":  a.scheduled_at.isoformat() if a.scheduled_at else None,
        "conducted_at":  a.conducted_at.isoformat() if a.conducted_at else None,
        "expected_count": a.expected_count,
        "actual_count":   a.actual_count,
        "female_count":   a.female_count,
        "vulnerable_count": a.vulnerable_count,
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


@router.get("/{project_id}", summary="Project landing page — details, stages, stakeholders, and activities")
async def get_project(project_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    project, counts = await _svc(db).get_with_counts(project_id)

    stakeholders = await StakeholderRepository(db).list(project_id=project_id, limit=200)
    activities   = await ActivityRepository(db).list(project_id=project_id, limit=200)

    return {
        **_project_out(project, include_stages=True),
        "counts":       counts,
        "stakeholders": [_stakeholder_brief(s) for s in stakeholders],
        "activities":   [_activity_brief(a) for a in activities],
    }
