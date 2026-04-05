# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/checklists.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/checklists.py
═══════════════════════════════════════════════════════════════════════════════
Checklist endpoints for projects, stages, and sub-projects.

All three entity levels share the same set of endpoints via an
`entity_type` path segment:

  Project-level:
    /orgs/{org_id}/projects/{project_id}/checklist

  Stage-level:
    /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist

  Sub-project-level:
    /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist

Routes (same pattern for each level):
  POST   .../checklist                    Add a checklist item
  GET    .../checklist                    List items + progress summary
  GET    .../checklist/progress           Progress summary only (lightweight)
  GET    .../checklist/{item_id}          Get a single item
  PATCH  .../checklist/{item_id}          Update item (any field)
  POST   .../checklist/{item_id}/done     Mark item as DONE (convenience)
  PUT    .../checklist/reorder            Bulk reorder (drag-and-drop)
  DELETE .../checklist/{item_id}          Soft-delete an item
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import get_db
from core.dependencies import require_org_role
from models.organisation import OrgMemberRole, OrganisationMember
from schemas.project import (
    ChecklistItemResponse,
    ChecklistListResponse,
    ChecklistProgressResponse,
    ChecklistPerformanceReport,
    CreateChecklistItemRequest,
    MarkDoneRequest,
    OrgChecklistPerformanceReport,
    ReorderChecklistRequest,
    StageChecklistPerformanceReport,
    SubProjectChecklistPerformanceReport,
    UpdateChecklistItemRequest,
)
from services.checklist_service import ChecklistService

router = APIRouter(tags=["Checklists"])

# ── Dependency helpers ────────────────────────────────────────────────────────

def _svc(db: AsyncSession = Depends(get_db)) -> ChecklistService:
    return ChecklistService(db=db)

_manager = Depends(require_org_role(OrgMemberRole.MANAGER))
_viewer  = Depends(require_org_role(OrgMemberRole.MEMBER))


# ═════════════════════════════════════════════════════════════════════════════
# Project-level checklist
# /orgs/{org_id}/projects/{project_id}/checklist
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/projects/{project_id}/checklist",
    status_code=status.HTTP_201_CREATED,
    response_model=ChecklistItemResponse,
    summary="Add a checklist item to a project",
    description=(
        "Add a new actionable item to the project's checklist. "
        "Only `title` is required. Optionally assign to a team member, "
        "set a due date, and categorise the item."
    ),
)
async def create_project_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    body:       CreateChecklistItemRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.create_item(
            entity_type="project",
            entity_id=project_id,
            data=body.model_dump(exclude_none=True),
            created_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/checklist",
    response_model=ChecklistListResponse,
    summary="List project checklist items with progress summary",
    description=(
        "Returns all checklist items for the project along with a progress "
        "summary (`done`, `in_progress`, `pending`, `percent_complete`). "
        "Filter by `status` or `category` for focused views."
    ),
)
async def list_project_checklist(
    org_id:      uuid.UUID,
    project_id:  uuid.UUID,
    status_:     Optional[str] = Query(default=None, alias="status",
                                        description="pending | in_progress | done | skipped | blocked"),
    category:    Optional[str] = Query(default=None, description="Filter by category label"),
    assigned_to: Optional[uuid.UUID] = Query(default=None),
    skip:  int = Query(default=0,   ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    svc:   ChecklistService = Depends(_svc),
    _:     Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistListResponse:
    result = await svc.list_items(
        "project", project_id, status_, category, assigned_to, skip, limit
    )
    return ChecklistListResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/checklist/progress",
    response_model=ChecklistProgressResponse,
    summary="Project checklist progress summary (lightweight)",
    description="Returns only the progress counts and percent_complete — no item list. Use for dashboard cards.",
)
async def project_checklist_progress(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistProgressResponse:
    result = await svc.progress("project", project_id)
    return ChecklistProgressResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Get a single project checklist item",
)
async def get_project_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    item_id:    uuid.UUID,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.get_item(item_id, "project", project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.patch(
    "/orgs/{org_id}/projects/{project_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Update a project checklist item",
    description=(
        "Update any field on the item. "
        "Setting `status = 'done'` auto-fills `completion_date` to today. "
        "Setting `status = 'skipped'` or `'blocked'` requires `skip_reason`."
    ),
)
async def update_project_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    item_id:    uuid.UUID,
    body:       UpdateChecklistItemRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.update_item(
            item_id, "project", project_id,
            body.model_dump(exclude_none=True),
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.post(
    "/orgs/{org_id}/projects/{project_id}/checklist/{item_id}/done",
    response_model=ChecklistItemResponse,
    summary="Mark a project checklist item as DONE",
    description=(
        "Convenience endpoint — marks the item as DONE in one call. "
        "Optionally provide a `completion_note` and `completion_evidence_url`. "
        "`completion_date` defaults to today."
    ),
)
async def mark_project_item_done(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    item_id:    uuid.UUID,
    body:       MarkDoneRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    from datetime import date
    comp_date = date.fromisoformat(body.completion_date) if body.completion_date else None
    try:
        result = await svc.mark_done(
            item_id, "project", project_id,
            completion_note=body.completion_note,
            evidence_url=body.completion_evidence_url,
            completion_date=comp_date,
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.put(
    "/orgs/{org_id}/projects/{project_id}/checklist/reorder",
    response_model=ChecklistListResponse,
    summary="Reorder project checklist items",
    description="Update display_order for multiple items in one request. Designed for drag-and-drop UIs.",
)
async def reorder_project_checklist(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    body:       ReorderChecklistRequest,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistListResponse:
    result = await svc.reorder("project", project_id, body.order)
    return ChecklistListResponse.from_dict(result)


@router.delete(
    "/orgs/{org_id}/projects/{project_id}/checklist/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a project checklist item",
    description="Soft-deletes the item. The record is preserved for audit purposes.",
)
async def delete_project_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    item_id:    uuid.UUID,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _manager] = ...,
) -> dict:
    try:
        await svc.delete_item(item_id, "project", project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Checklist item {item_id} deleted."}


# ═════════════════════════════════════════════════════════════════════════════
# Stage-level checklist
# /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist",
    status_code=status.HTTP_201_CREATED,
    response_model=ChecklistItemResponse,
    summary="Add a checklist item to a stage",
)
async def create_stage_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    body:       CreateChecklistItemRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.create_item(
            "stage", stage_id,
            body.model_dump(exclude_none=True),
            created_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist",
    response_model=ChecklistListResponse,
    summary="List stage checklist items with progress summary",
)
async def list_stage_checklist(
    org_id:      uuid.UUID,
    project_id:  uuid.UUID,
    stage_id:    uuid.UUID,
    status_:     Optional[str] = Query(default=None, alias="status"),
    category:    Optional[str] = Query(default=None),
    assigned_to: Optional[uuid.UUID] = Query(default=None),
    skip:  int = Query(default=0,   ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    svc:   ChecklistService = Depends(_svc),
    _:     Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistListResponse:
    result = await svc.list_items(
        "stage", stage_id, status_, category, assigned_to, skip, limit
    )
    return ChecklistListResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/progress",
    response_model=ChecklistProgressResponse,
    summary="Stage checklist progress summary",
)
async def stage_checklist_progress(
    org_id:    uuid.UUID,
    project_id: uuid.UUID,
    stage_id:  uuid.UUID,
    svc:       ChecklistService = Depends(_svc),
    _:         Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistProgressResponse:
    result = await svc.progress("stage", stage_id)
    return ChecklistProgressResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Get a single stage checklist item",
)
async def get_stage_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    item_id:    uuid.UUID,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.get_item(item_id, "stage", stage_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.patch(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Update a stage checklist item",
)
async def update_stage_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    item_id:    uuid.UUID,
    body:       UpdateChecklistItemRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.update_item(
            item_id, "stage", stage_id,
            body.model_dump(exclude_none=True),
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.post(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/{item_id}/done",
    response_model=ChecklistItemResponse,
    summary="Mark a stage checklist item as DONE",
)
async def mark_stage_item_done(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    item_id:    uuid.UUID,
    body:       MarkDoneRequest,
    svc:        ChecklistService = Depends(_svc),
    membership: Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    from datetime import date
    comp_date = date.fromisoformat(body.completion_date) if body.completion_date else None
    try:
        result = await svc.mark_done(
            item_id, "stage", stage_id,
            completion_note=body.completion_note,
            evidence_url=body.completion_evidence_url,
            completion_date=comp_date,
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.put(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/reorder",
    response_model=ChecklistListResponse,
    summary="Reorder stage checklist items",
)
async def reorder_stage_checklist(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    body:       ReorderChecklistRequest,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistListResponse:
    result = await svc.reorder("stage", stage_id, body.order)
    return ChecklistListResponse.from_dict(result)


@router.delete(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a stage checklist item",
)
async def delete_stage_checklist_item(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    item_id:    uuid.UUID,
    svc:        ChecklistService = Depends(_svc),
    _:          Annotated[OrganisationMember, _manager] = ...,
) -> dict:
    try:
        await svc.delete_item(item_id, "stage", stage_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Checklist item {item_id} deleted."}


# ═════════════════════════════════════════════════════════════════════════════
# Sub-project-level checklist
# /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist",
    status_code=status.HTTP_201_CREATED,
    response_model=ChecklistItemResponse,
    summary="Add a checklist item to a sub-project",
)
async def create_subproject_checklist_item(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    body:          CreateChecklistItemRequest,
    svc:           ChecklistService = Depends(_svc),
    membership:    Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.create_item(
            "subproject", subproject_id,
            body.model_dump(exclude_none=True),
            created_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist",
    response_model=ChecklistListResponse,
    summary="List sub-project checklist items with progress summary",
)
async def list_subproject_checklist(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    status_:       Optional[str] = Query(default=None, alias="status"),
    category:      Optional[str] = Query(default=None),
    assigned_to:   Optional[uuid.UUID] = Query(default=None),
    skip:  int = Query(default=0,   ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    svc:   ChecklistService = Depends(_svc),
    _:     Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistListResponse:
    result = await svc.list_items(
        "subproject", subproject_id, status_, category, assigned_to, skip, limit
    )
    return ChecklistListResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/progress",
    response_model=ChecklistProgressResponse,
    summary="Sub-project checklist progress summary",
)
async def subproject_checklist_progress(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ChecklistService = Depends(_svc),
    _:             Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistProgressResponse:
    result = await svc.progress("subproject", subproject_id)
    return ChecklistProgressResponse.from_dict(result)


@router.get(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Get a single sub-project checklist item",
)
async def get_subproject_checklist_item(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    item_id:       uuid.UUID,
    svc:           ChecklistService = Depends(_svc),
    _:             Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.get_item(item_id, "subproject", subproject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.patch(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
    summary="Update a sub-project checklist item",
)
async def update_subproject_checklist_item(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    item_id:       uuid.UUID,
    body:          UpdateChecklistItemRequest,
    svc:           ChecklistService = Depends(_svc),
    membership:    Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    try:
        result = await svc.update_item(
            item_id, "subproject", subproject_id,
            body.model_dump(exclude_none=True),
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.post(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/{item_id}/done",
    response_model=ChecklistItemResponse,
    summary="Mark a sub-project checklist item as DONE",
)
async def mark_subproject_item_done(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    item_id:       uuid.UUID,
    body:          MarkDoneRequest,
    svc:           ChecklistService = Depends(_svc),
    membership:    Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistItemResponse:
    from datetime import date
    comp_date = date.fromisoformat(body.completion_date) if body.completion_date else None
    try:
        result = await svc.mark_done(
            item_id, "subproject", subproject_id,
            completion_note=body.completion_note,
            evidence_url=body.completion_evidence_url,
            completion_date=comp_date,
            updated_by_user_id=membership.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChecklistItemResponse.from_dict(result)


@router.put(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/reorder",
    response_model=ChecklistListResponse,
    summary="Reorder sub-project checklist items",
)
async def reorder_subproject_checklist(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    body:          ReorderChecklistRequest,
    svc:           ChecklistService = Depends(_svc),
    _:             Annotated[OrganisationMember, _manager] = ...,
) -> ChecklistListResponse:
    result = await svc.reorder("subproject", subproject_id, body.order)
    return ChecklistListResponse.from_dict(result)


@router.delete(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a sub-project checklist item",
)
async def delete_subproject_checklist_item(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    item_id:       uuid.UUID,
    svc:           ChecklistService = Depends(_svc),
    _:             Annotated[OrganisationMember, _manager] = ...,
) -> dict:
    try:
        await svc.delete_item(item_id, "subproject", subproject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Checklist item {item_id} deleted."}


# ═════════════════════════════════════════════════════════════════════════════
# Checklist Performance Reports
# ═════════════════════════════════════════════════════════════════════════════
#
# Two report scopes:
#   1. Project-level  — one row per entity (project + stages + sub-projects)
#      GET /orgs/{org_id}/projects/{project_id}/checklist-performance
#
#   2. Org-level      — one aggregated row per project
#      GET /orgs/{org_id}/checklist-performance
#
# Both support filtering by entity_type, status, region, lga.
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/orgs/{org_id}/projects/{project_id}/checklist-performance",
    response_model=ChecklistPerformanceReport,
    summary="Checklist performance report for a project",
    description=(
        "Returns a full performance breakdown for one project — one row per "
        "entity (the project itself, each stage, and each sub-project). "
        "Each row shows the entity name, status, location context, and "
        "checklist stats: total, done, in_progress, pending, skipped, "
        "blocked, **overdue** (past due date), and percent complete.\n\n"
        "Filter by `entity_type` to see only stages, only sub-projects, etc. "
        "Filter by `status` to focus on active or planning entities only.\n\n"
        "The `summary` block aggregates across all rows for a single "
        "top-level progress bar."
    ),
)
async def project_checklist_performance(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter rows by entity level: project | stage | subproject",
    ),
    status: Optional[str] = Query(
        default=None,
        description=(
            "Filter rows by entity status. "
            "For projects: planning | active | paused | completed | cancelled. "
            "For stages: pending | active | completed | skipped. "
            "For subprojects: pending | active | completed | cancelled."
        ),
    ),
    overdue_only: bool = Query(
        default=False,
        description="When true, return only rows that have at least one overdue checklist item.",
    ),
    svc: ChecklistService = Depends(_svc),
    _:   Annotated[OrganisationMember, _viewer] = ...,
) -> ChecklistPerformanceReport:
    result = await svc.performance_report_by_project(
        org_id=org_id,
        project_id=project_id,
        entity_type=entity_type,
        status_filter=status,
    )
    if overdue_only:
        result["rows"] = [r for r in result["rows"] if r.get("overdue", 0) > 0]
    return ChecklistPerformanceReport.from_dict(result)


@router.get(
    "/orgs/{org_id}/checklist-performance",
    response_model=OrgChecklistPerformanceReport,
    summary="Checklist performance report across all projects in an organisation",
    description=(
        "Portfolio-level checklist performance — one aggregated row per project. "
        "Combines all checklist items (project + stages + sub-projects) into "
        "a single row per project showing total, done, overdue, and "
        "percent_complete.\n\n"
        "Use this endpoint for executive dashboards and portfolio-level reporting.\n\n"
        "Supports filtering by `status` (project status), `region`, and `lga` "
        "to focus on e.g. only active projects in a specific region."
    ),
)
async def org_checklist_performance(
    org_id: uuid.UUID,
    status: Optional[str] = Query(
        default=None,
        description="Filter by project status: planning | active | paused | completed | cancelled",
    ),
    region: Optional[str] = Query(
        default=None,
        description="Filter by project region (exact match, case-insensitive).",
    ),
    lga: Optional[str] = Query(
        default=None,
        description="Filter by project primary_lga (exact match, case-insensitive).",
    ),
    overdue_only: bool = Query(
        default=False,
        description="When true, return only project rows that have at least one overdue item.",
    ),
    svc: ChecklistService = Depends(_svc),
    _:   Annotated[OrganisationMember, _viewer] = ...,
) -> OrgChecklistPerformanceReport:
    result = await svc.performance_report_by_org(
        org_id=org_id,
        status_filter=status,
        region=region,
        lga=lga,
    )
    if overdue_only:
        result["rows"] = [r for r in result["rows"] if r.get("overdue", 0) > 0]
    return OrgChecklistPerformanceReport.from_dict(result)


# ── Stage-level performance ────────────────────────────────────────────────────

@router.get(
    "/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist-performance",
    response_model=StageChecklistPerformanceReport,
    summary="Checklist performance report for a stage",
    description=(
        "Returns a performance breakdown for one stage — the stage row itself "
        "plus one row per sub-project belonging to it.\n\n"
        "Every row carries the stage timeline (start, end, actual dates), "
        "objectives, deliverables, and parent project location.\n\n"
        "Sub-project rows additionally include sub-project dates, budget, "
        "objectives, expected outputs, and parent sub-project reference.\n\n"
        "The `summary` block aggregates across all rows (stage + all its "
        "sub-projects) for a single stage-level progress bar.\n\n"
        "**Filter options:**\n"
        "- `entity_type=subproject` — show only sub-project rows, skip the stage row\n"
        "- `status=active` — show only active entities\n"
        "- `overdue_only=true` — show only entities with overdue items"
    ),
)
async def stage_checklist_performance(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter: stage | subproject",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by entity status: pending | active | completed | skipped | cancelled",
    ),
    overdue_only: bool = Query(
        default=False,
        description="When true, return only rows that have at least one overdue item.",
    ),
    svc: ChecklistService = Depends(_svc),
    _:   Annotated[OrganisationMember, _viewer] = ...,
) -> StageChecklistPerformanceReport:
    result = await svc.performance_report_by_stage(
        stage_id=stage_id,
        entity_type=entity_type,
        status_filter=status,
    )
    # Apply overdue_only filter post-fetch
    if overdue_only:
        result["rows"] = [r for r in result["rows"] if r.get("overdue", 0) > 0]
    return StageChecklistPerformanceReport.from_dict(result)


# ── Sub-project-level performance ──────────────────────────────────────────────

@router.get(
    "/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist-performance",
    response_model=SubProjectChecklistPerformanceReport,
    summary="Checklist performance for a single sub-project",
    description=(
        "Returns a single-entity performance report for one sub-project.\n\n"
        "Includes full context: stage name/order/status, parent project "
        "name/region/LGA/location, sub-project dates, budget, objectives, "
        "and expected outputs — alongside the full checklist stats "
        "(total, done, in_progress, pending, skipped, blocked, overdue, "
        "percent_complete).\n\n"
        "Use this when drilling down into a specific work package — "
        "e.g. when a contractor or site engineer needs to see the checklist "
        "status for their specific sub-project without the broader context."
    ),
)
async def subproject_checklist_performance(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ChecklistService = Depends(_svc),
    _:             Annotated[OrganisationMember, _viewer] = ...,
) -> SubProjectChecklistPerformanceReport:
    from fastapi import HTTPException
    try:
        result = await svc.performance_report_by_subproject(subproject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SubProjectChecklistPerformanceReport.from_dict(result)
