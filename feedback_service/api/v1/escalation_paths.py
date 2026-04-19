# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service  |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  api/v1/escalation_paths.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/escalation_paths.py
REST API for managing dynamic per-organisation GRM escalation hierarchies.

Endpoints:
  POST   /escalation-paths                              — Create org path
  POST   /escalation-paths/from-template                — Clone system template
  GET    /escalation-paths                              — List org paths
  GET    /escalation-paths/system-templates             — List system templates
  GET    /escalation-paths/{path_id}                    — Get path with levels
  PATCH  /escalation-paths/{path_id}                   — Update path metadata
  DELETE /escalation-paths/{path_id}                   — Deactivate path
  POST   /escalation-paths/{path_id}/levels             — Add level to path
  PATCH  /escalation-paths/{path_id}/levels/{level_id} — Update level
  DELETE /escalation-paths/{path_id}/levels/{level_id} — Remove level
  POST   /escalation-paths/{path_id}/levels/reorder     — Reorder levels
"""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, status

from core.dependencies import DbDep, GRMCoordinatorDep, GRMOfficerDep, StaffDep
from schemas.escalation import (
    EscalationLevelCreate,
    EscalationLevelResponse,
    EscalationLevelUpdate,
    EscalationPathClone,
    EscalationPathCreate,
    EscalationPathListResponse,
    EscalationPathResponse,
    EscalationPathUpdate,
    EscalationLevelReorder,
)
from services.escalation_service import EscalationService

router = APIRouter(prefix="/escalation-paths", tags=["Escalation Paths"])


def _svc(db: DbDep) -> EscalationService:
    return EscalationService(db)


# ── Path endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EscalationPathResponse,
    summary="Create a new escalation path for the org",
)
async def create_escalation_path(
    body: EscalationPathCreate,
    db: DbDep,
    token: GRMCoordinatorDep,
) -> EscalationPathResponse:
    """
    Create a custom escalation hierarchy for the current organisation.

    Supply `levels` inline to define the chain in a single call, or leave it
    empty and add levels individually via POST .../levels.

    `is_default=true` clears the previous default for this org.
    """
    org_id = token.org_id
    path = await _svc(db).create_path(
        org_id=org_id,
        data=body.model_dump(exclude_none=True),
        created_by=token.sub,
    )
    return EscalationPathResponse.model_validate(path)


@router.post(
    "/from-template",
    status_code=status.HTTP_201_CREATED,
    response_model=EscalationPathResponse,
    summary="Clone a system template into an editable org path",
)
async def clone_from_template(
    body: EscalationPathClone,
    db: DbDep,
    token: GRMCoordinatorDep,
) -> EscalationPathResponse:
    """
    Clone a system template (or any other path) to get a fully editable copy
    scoped to the current organisation. All levels are deep-copied.
    """
    path = await _svc(db).clone_from_template(
        template_id=body.template_id,
        org_id=token.org_id,
        name=body.name,
        created_by=token.sub,
        set_as_default=body.set_as_default,
    )
    return EscalationPathResponse.model_validate(path)


@router.get(
    "",
    response_model=EscalationPathListResponse,
    summary="List all escalation paths for the current org",
)
async def list_escalation_paths(
    db: DbDep,
    token: StaffDep,
) -> EscalationPathListResponse:
    """Returns all active escalation paths for the current organisation."""
    paths = await _svc(db).list_paths(token.org_id)
    items = [EscalationPathResponse.model_validate(p) for p in paths]
    return EscalationPathListResponse(total=len(items), items=items)


@router.get(
    "/system-templates",
    response_model=List[EscalationPathResponse],
    summary="List read-only system templates",
)
async def list_system_templates(
    db: DbDep,
    token: StaffDep,
) -> List[EscalationPathResponse]:
    """
    Returns all system-level template paths (is_system_template=True).
    These are read-only — clone one to create an editable copy for your org.
    """
    templates = await _svc(db).list_system_templates()
    return [EscalationPathResponse.model_validate(t) for t in templates]


@router.get(
    "/{path_id}",
    response_model=EscalationPathResponse,
    summary="Get a single escalation path with all levels",
)
async def get_escalation_path(
    path_id: uuid.UUID,
    db: DbDep,
    token: StaffDep,
) -> EscalationPathResponse:
    path = await _svc(db).get_path_or_404(path_id)
    return EscalationPathResponse.model_validate(path)


@router.patch(
    "/{path_id}",
    response_model=EscalationPathResponse,
    summary="Update path metadata (name, description, is_default, is_active)",
)
async def update_escalation_path(
    path_id: uuid.UUID,
    body: EscalationPathUpdate,
    db: DbDep,
    token: GRMCoordinatorDep,
) -> EscalationPathResponse:
    """
    Update the path metadata. Cannot modify system templates.
    Setting `is_default=true` clears the previous default for this org.
    """
    path = await _svc(db).update_path(
        path_id=path_id,
        data=body.model_dump(exclude_none=True),
        org_id=token.org_id,
    )
    return EscalationPathResponse.model_validate(path)


@router.delete(
    "/{path_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate an escalation path (soft delete)",
)
async def delete_escalation_path(
    path_id: uuid.UUID,
    db: DbDep,
    token: GRMCoordinatorDep,
) -> None:
    """
    Soft-deletes the path by setting is_active=False.
    System templates cannot be deleted.
    """
    await _svc(db).delete_path(path_id=path_id, org_id=token.org_id)


# ── Level endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/{path_id}/levels",
    status_code=status.HTTP_201_CREATED,
    response_model=EscalationLevelResponse,
    summary="Add a level to an escalation path",
)
async def add_level(
    path_id: uuid.UUID,
    body: EscalationLevelCreate,
    db: DbDep,
    token: GRMOfficerDep,
) -> EscalationLevelResponse:
    """
    Add a new level to an existing path.
    `level_order` must be unique within the path.
    Use POST .../levels/reorder to renumber existing levels first if needed.
    """
    level = await _svc(db).add_level(
        path_id=path_id,
        data=body.model_dump(exclude_none=True),
        org_id=token.org_id,
    )
    return EscalationLevelResponse.model_validate(level)


@router.post(
    "/{path_id}/levels/reorder",
    response_model=EscalationPathResponse,
    summary="Reorder levels by providing all level IDs in the desired order",
)
async def reorder_levels(
    path_id: uuid.UUID,
    body: EscalationLevelReorder,
    db: DbDep,
    token: GRMOfficerDep,
) -> EscalationPathResponse:
    """
    Reassign `level_order` values based on the provided ordered list.
    The first ID in `ordered_level_ids` becomes level_order=1, etc.
    All level IDs belonging to this path must be included.
    """
    path = await _svc(db).reorder_levels(
        path_id=path_id,
        ordered_level_ids=body.ordered_level_ids,
        org_id=token.org_id,
    )
    return EscalationPathResponse.model_validate(path)


@router.patch(
    "/{path_id}/levels/{level_id}",
    response_model=EscalationLevelResponse,
    summary="Update an escalation level (SLA, name, auto-escalation config)",
)
async def update_level(
    path_id: uuid.UUID,
    level_id: uuid.UUID,
    body: EscalationLevelUpdate,
    db: DbDep,
    token: GRMOfficerDep,
) -> EscalationLevelResponse:
    """
    Update any field on a level — name, SLA hours, per-priority SLA overrides,
    auto-escalation settings, responsible role, or notification emails.
    """
    level = await _svc(db).update_level(
        path_id=path_id,
        level_id=level_id,
        data=body.model_dump(exclude_none=True),
        org_id=token.org_id,
    )
    return EscalationLevelResponse.model_validate(level)


@router.delete(
    "/{path_id}/levels/{level_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a level from an escalation path",
)
async def remove_level(
    path_id: uuid.UUID,
    level_id: uuid.UUID,
    db: DbDep,
    token: GRMOfficerDep,
) -> None:
    """
    Hard-deletes the level row. Consider reordering remaining levels afterwards.
    """
    await _svc(db).remove_level(
        path_id=path_id,
        level_id=level_id,
        org_id=token.org_id,
    )
