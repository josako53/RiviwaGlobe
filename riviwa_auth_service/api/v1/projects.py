# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/projects.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/projects.py
═══════════════════════════════════════════════════════════════════════════════
Execution project endpoints — OrgProject, Stages, Sub-projects, In-charges.

All routes sit under /api/v1/orgs/{org_id}/projects/...
Minimum role: MANAGER for reads, ADMIN for writes, OWNER for status changes.

Route inventory
────────────────
  Projects
    POST   /orgs/{org_id}/projects
    GET    /orgs/{org_id}/projects
    GET    /orgs/{org_id}/projects/{project_id}
    PATCH  /orgs/{org_id}/projects/{project_id}
    POST   /orgs/{org_id}/projects/{project_id}/activate    PLANNING → ACTIVE
    POST   /orgs/{org_id}/projects/{project_id}/pause       ACTIVE → PAUSED
    POST   /orgs/{org_id}/projects/{project_id}/resume      PAUSED → ACTIVE
    POST   /orgs/{org_id}/projects/{project_id}/complete    → COMPLETED
    DELETE /orgs/{org_id}/projects/{project_id}             soft-delete → CANCELLED

  In-charges (project level)
    POST   /orgs/{org_id}/projects/{project_id}/in-charges
    GET    /orgs/{org_id}/projects/{project_id}/in-charges
    DELETE /orgs/{org_id}/projects/{project_id}/in-charges/{user_id}

  Stages
    POST   /orgs/{org_id}/projects/{project_id}/stages
    GET    /orgs/{org_id}/projects/{project_id}/stages
    GET    /orgs/{org_id}/projects/{project_id}/stages/{stage_id}
    PATCH  /orgs/{org_id}/projects/{project_id}/stages/{stage_id}
    POST   /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/activate
    POST   /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/complete
    POST   /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/skip

  Stage in-charges
    POST   /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges
    GET    /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges
    DELETE /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges/{user_id}

  Sub-projects
    POST   /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/subprojects
    GET    /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/subprojects
    GET    /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}
    GET    /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/tree
    PATCH  /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}
    DELETE /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}

  Sub-project in-charges
    POST   /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges
    GET    /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges
    DELETE /orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges/{user_id}
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from schemas.project import (
    UploadProgressImageRequest,
    UpdateProgressImageRequest,
    ProgressImageResponse,
    ProgressImageListResponse,
)

import uuid
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import get_db, get_publisher
from core.dependencies import DbDep, require_active_user, require_org_role, require_platform_role
from core.exceptions import NotFoundError
from models.organisation import OrgMemberRole, OrganisationMember
from schemas.common import MessageResponse
from schemas.project import (
    CreateProjectInChargeRequest,
    CreateProjectRequest,
    CreateStageInChargeRequest,
    CreateStageRequest,
    CreateSubProjectInChargeRequest,
    CreateSubProjectRequest,
    ProjectDetailResponse,
    ProjectInChargeResponse,
    ProjectSummaryResponse,
    StageInChargeResponse,
    StageResponse,
    SubProjectInChargeResponse,
    SubProjectResponse,
    UpdateProjectRequest,
    UpdateStageRequest,
    UpdateSubProjectRequest,
)
from services.project_service import ProjectService

router = APIRouter(prefix="/orgs", tags=["Projects"])

# ── Role guards ───────────────────────────────────────────────────────────────
_manager_guard = Depends(require_org_role(OrgMemberRole.MANAGER))
_admin_guard   = Depends(require_org_role(OrgMemberRole.ADMIN))
_owner_guard   = Depends(require_org_role(OrgMemberRole.OWNER))


# ── Dependency: ProjectService with publisher ─────────────────────────────────

async def get_project_service(
    db:        AsyncSession = Depends(get_db),
    publisher: object       = Depends(get_publisher),
) -> ProjectService:
    return ProjectService(db=db, publisher=publisher)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


# ═════════════════════════════════════════════════════════════════════════════
# Projects
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an execution project",
    dependencies=[_admin_guard],
)
async def create_project(
    org_id: uuid.UUID,
    body:   CreateProjectRequest,
    user:   Annotated[object, Depends(require_active_user)],
    svc:    ProjectServiceDep,
) -> ProjectSummaryResponse:
    """
    Create a new execution project in PLANNING status.
    Requires ADMIN role within the organisation.

    The project is not visible to stakeholder/feedback services until it
    is activated (PLANNING → ACTIVE). Activation publishes a Kafka event
    that triggers ProjectCache creation in both downstream services.
    """
    data    = body.model_dump(exclude_none=True)
    project = await svc.create_project(org_id, data, created_by_id=user.id)
    return ProjectSummaryResponse.model_validate(project)


@router.get(
    "/{org_id}/projects",
    response_model=list[ProjectSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List projects for this organisation",
    dependencies=[_manager_guard],
)
async def list_projects(
    org_id:    uuid.UUID,
    svc:       ProjectServiceDep,
    status_:   Optional[str]       = Query(default=None, alias="status",
                                           description="planning|active|paused|completed|cancelled"),
    branch_id: Optional[uuid.UUID] = Query(default=None),
    skip:      int                  = Query(default=0, ge=0),
    limit:     int                  = Query(default=50, ge=1, le=200),
) -> list[ProjectSummaryResponse]:
    projects = await svc.list_projects(org_id, status_, branch_id, skip, limit)
    return [ProjectSummaryResponse.model_validate(p) for p in projects]


@router.get(
    "/{org_id}/projects/{project_id}",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Project detail with stages and in-charges",
    dependencies=[_manager_guard],
)
async def get_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> ProjectDetailResponse:
    project = await svc.get_project(org_id, project_id)
    return ProjectDetailResponse.model_validate(project)


@router.patch(
    "/{org_id}/projects/{project_id}",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project fields",
    dependencies=[_admin_guard],
)
async def update_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    body:       UpdateProjectRequest,
    svc:        ProjectServiceDep,
) -> ProjectSummaryResponse:
    fields  = body.model_dump(exclude_none=True)
    project = await svc.update_project(org_id, project_id, **fields)
    return ProjectSummaryResponse.model_validate(project)


@router.post(
    "/{org_id}/projects/{project_id}/activate",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate project (PLANNING → ACTIVE)",
    dependencies=[_owner_guard],
)
async def activate_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> ProjectSummaryResponse:
    """
    Transitions the project from PLANNING to ACTIVE.
    Publishes org_project.published on riviwa.org.events — this triggers
    stakeholder_service and feedback_service to create their local ProjectCache.
    """
    project = await svc.activate_project(org_id, project_id)
    return ProjectSummaryResponse.model_validate(project)


@router.post(
    "/{org_id}/projects/{project_id}/pause",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause project (ACTIVE → PAUSED)",
    dependencies=[_owner_guard],
)
async def pause_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> ProjectSummaryResponse:
    project = await svc.pause_project(org_id, project_id)
    return ProjectSummaryResponse.model_validate(project)


@router.post(
    "/{org_id}/projects/{project_id}/resume",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume project (PAUSED → ACTIVE)",
    dependencies=[_owner_guard],
)
async def resume_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> ProjectSummaryResponse:
    project = await svc.resume_project(org_id, project_id)
    return ProjectSummaryResponse.model_validate(project)


@router.post(
    "/{org_id}/projects/{project_id}/complete",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark project as completed",
    dependencies=[_owner_guard],
)
async def complete_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> ProjectSummaryResponse:
    project = await svc.complete_project(org_id, project_id)
    return ProjectSummaryResponse.model_validate(project)


@router.delete(
    "/{org_id}/projects/{project_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel and soft-delete project",
    dependencies=[_owner_guard],
)
async def cancel_project(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> MessageResponse:
    await svc.cancel_project(org_id, project_id)
    return MessageResponse(message="Project cancelled and archived.")


# ═════════════════════════════════════════════════════════════════════════════
# Project In-charges
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects/{project_id}/in-charges",
    response_model=ProjectInChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a person to the project leadership team",
    dependencies=[_admin_guard],
)
async def assign_project_in_charge(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    body:       CreateProjectInChargeRequest,
    svc:        ProjectServiceDep,
) -> ProjectInChargeResponse:
    inc = await svc.assign_in_charge(org_id, project_id, body.model_dump())
    return ProjectInChargeResponse.model_validate(inc)


@router.get(
    "/{org_id}/projects/{project_id}/in-charges",
    response_model=list[ProjectInChargeResponse],
    status_code=status.HTTP_200_OK,
    summary="List project leadership team",
    dependencies=[_manager_guard],
)
async def list_project_in_charges(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> list[ProjectInChargeResponse]:
    items = await svc.list_in_charges(org_id, project_id)
    return [ProjectInChargeResponse.model_validate(i) for i in items]


@router.delete(
    "/{org_id}/projects/{project_id}/in-charges/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Relieve a person from the project leadership team",
    dependencies=[_admin_guard],
)
async def relieve_project_in_charge(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    user_id:    uuid.UUID,
    svc:        ProjectServiceDep,
    role_title: str = Query(..., description="Role title to relieve. Required since a user can hold multiple roles."),
) -> MessageResponse:
    await svc.relieve_in_charge(org_id, project_id, user_id, role_title)
    return MessageResponse(message="In-charge relieved.")


# ═════════════════════════════════════════════════════════════════════════════
# Stages
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects/{project_id}/stages",
    response_model=StageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a stage to the project",
    dependencies=[_admin_guard],
)
async def add_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    body:       CreateStageRequest,
    svc:        ProjectServiceDep,
) -> StageResponse:
    stage = await svc.add_stage(org_id, project_id, body.model_dump(exclude_none=True))
    return StageResponse.model_validate(stage)


@router.get(
    "/{org_id}/projects/{project_id}/stages",
    response_model=list[StageResponse],
    status_code=status.HTTP_200_OK,
    summary="List stages in order",
    dependencies=[_manager_guard],
)
async def list_stages(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    svc:        ProjectServiceDep,
) -> list[StageResponse]:
    stages = await svc.list_stages(org_id, project_id)
    return [StageResponse.model_validate(s) for s in stages]


@router.get(
    "/{org_id}/projects/{project_id}/stages/{stage_id}",
    response_model=StageResponse,
    status_code=status.HTTP_200_OK,
    summary="Stage detail with in-charges and sub-projects",
    dependencies=[_manager_guard],
)
async def get_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    svc:        ProjectServiceDep,
) -> StageResponse:
    stage = await svc.get_stage(org_id, project_id, stage_id)
    return StageResponse.model_validate(stage)


@router.patch(
    "/{org_id}/projects/{project_id}/stages/{stage_id}",
    response_model=StageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update stage fields",
    dependencies=[_admin_guard],
)
async def update_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    body:       UpdateStageRequest,
    svc:        ProjectServiceDep,
) -> StageResponse:
    fields = body.model_dump(exclude_none=True)
    stage  = await svc.update_stage(org_id, project_id, stage_id, **fields)
    return StageResponse.model_validate(stage)


@router.post(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/activate",
    response_model=StageResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate stage (PENDING → ACTIVE)",
    dependencies=[_admin_guard],
)
async def activate_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    svc:        ProjectServiceDep,
) -> StageResponse:
    """
    PENDING → ACTIVE. Only one stage can be active at a time.
    Publishes org_project_stage.activated — downstream services update
    their ProjectStageCache and apply stage-level feedback acceptance flags.
    """
    stage = await svc.activate_stage(org_id, project_id, stage_id)
    return StageResponse.model_validate(stage)


@router.post(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/complete",
    response_model=StageResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete stage (ACTIVE → COMPLETED)",
    dependencies=[_admin_guard],
)
async def complete_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    svc:        ProjectServiceDep,
) -> StageResponse:
    stage = await svc.complete_stage(org_id, project_id, stage_id)
    return StageResponse.model_validate(stage)


@router.post(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/skip",
    response_model=StageResponse,
    status_code=status.HTTP_200_OK,
    summary="Skip stage — mark as out-of-scope (PENDING → SKIPPED)",
    dependencies=[_admin_guard],
)
async def skip_stage(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    svc:        ProjectServiceDep,
) -> StageResponse:
    stage = await svc.skip_stage(org_id, project_id, stage_id)
    return StageResponse.model_validate(stage)


# ═════════════════════════════════════════════════════════════════════════════
# Stage In-charges
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges",
    response_model=StageInChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a person to a stage",
    dependencies=[_admin_guard],
)
async def assign_stage_in_charge(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    body:       CreateStageInChargeRequest,
    svc:        ProjectServiceDep,
) -> StageInChargeResponse:
    inc = await svc.assign_stage_in_charge(
        org_id, project_id, stage_id, body.model_dump()
    )
    return StageInChargeResponse.model_validate(inc)


@router.get(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges",
    response_model=list[StageInChargeResponse],
    status_code=status.HTTP_200_OK,
    summary="List stage in-charges",
    dependencies=[_manager_guard],
)
async def list_stage_in_charges(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    svc:        ProjectServiceDep,
) -> list[StageInChargeResponse]:
    items = await svc.list_stage_in_charges(org_id, project_id, stage_id)
    return [StageInChargeResponse.model_validate(i) for i in items]


@router.delete(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/in-charges/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Relieve a person from a stage",
    dependencies=[_admin_guard],
)
async def relieve_stage_in_charge(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    user_id:    uuid.UUID,
    svc:        ProjectServiceDep,
    role_title: str = Query(...),
) -> MessageResponse:
    await svc.relieve_stage_in_charge(org_id, project_id, stage_id, user_id, role_title)
    return MessageResponse(message="Stage in-charge relieved.")


# ═════════════════════════════════════════════════════════════════════════════
# Sub-projects
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/subprojects",
    response_model=SubProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sub-project within a stage",
    dependencies=[_admin_guard],
)
async def create_subproject(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    stage_id:   uuid.UUID,
    body:       CreateSubProjectRequest,
    svc:        ProjectServiceDep,
) -> SubProjectResponse:
    """
    Create a work package within a stage. Set parent_subproject_id to nest
    under an existing sub-project. Depth is unlimited.
    """
    sp = await svc.add_subproject(
        org_id, project_id, stage_id,
        body.model_dump(exclude_none=True),
    )
    return SubProjectResponse.model_validate(sp)


@router.get(
    "/{org_id}/projects/{project_id}/stages/{stage_id}/subprojects",
    response_model=list[SubProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List sub-projects for a stage",
    dependencies=[_manager_guard],
)
async def list_subprojects(
    org_id:      uuid.UUID,
    project_id:  uuid.UUID,
    stage_id:    uuid.UUID,
    svc:         ProjectServiceDep,
    parent_only: bool = Query(default=True, description="True = top-level only (no parent). False = all."),
) -> list[SubProjectResponse]:
    items = await svc.list_subprojects(org_id, project_id, stage_id, parent_only)
    return [SubProjectResponse.model_validate(sp) for sp in items]


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}",
    response_model=SubProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Sub-project detail with in-charges and direct children",
    dependencies=[_manager_guard],
)
async def get_subproject(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ProjectServiceDep,
) -> SubProjectResponse:
    sp = await svc.get_subproject(org_id, project_id, subproject_id)
    return SubProjectResponse.model_validate(sp)


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/tree",
    response_model=list[uuid.UUID],
    status_code=status.HTTP_200_OK,
    summary="All sub-project IDs in the subtree (WITH RECURSIVE)",
    dependencies=[_manager_guard],
)
async def get_subproject_tree(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ProjectServiceDep,
) -> list[uuid.UUID]:
    """
    Returns all descendant sub-project IDs (including the root) using a
    PostgreSQL WITH RECURSIVE CTE. Use to scope queries to an entire
    sub-tree without loading each level individually.
    """
    return await svc.get_subproject_tree(org_id, project_id, subproject_id)


@router.patch(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}",
    response_model=SubProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update sub-project fields",
    dependencies=[_admin_guard],
)
async def update_subproject(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    body:          UpdateSubProjectRequest,
    svc:           ProjectServiceDep,
) -> SubProjectResponse:
    fields = body.model_dump(exclude_none=True)
    sp     = await svc.update_subproject(org_id, project_id, subproject_id, **fields)
    return SubProjectResponse.model_validate(sp)


@router.delete(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a sub-project (status → CANCELLED)",
    dependencies=[_admin_guard],
)
async def delete_subproject(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ProjectServiceDep,
) -> MessageResponse:
    await svc.delete_subproject(org_id, project_id, subproject_id)
    return MessageResponse(message="Sub-project cancelled and archived.")


# ═════════════════════════════════════════════════════════════════════════════
# Sub-project In-charges
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges",
    response_model=SubProjectInChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a person to a sub-project",
    dependencies=[_admin_guard],
)
async def assign_subproject_in_charge(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    body:          CreateSubProjectInChargeRequest,
    svc:           ProjectServiceDep,
) -> SubProjectInChargeResponse:
    inc = await svc.assign_subproject_in_charge(
        org_id, project_id, subproject_id, body.model_dump()
    )
    return SubProjectInChargeResponse.model_validate(inc)


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges",
    response_model=list[SubProjectInChargeResponse],
    status_code=status.HTTP_200_OK,
    summary="List sub-project in-charges",
    dependencies=[_manager_guard],
)
async def list_subproject_in_charges(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    svc:           ProjectServiceDep,
) -> list[SubProjectInChargeResponse]:
    items = await svc.list_subproject_in_charges(org_id, project_id, subproject_id)
    return [SubProjectInChargeResponse.model_validate(i) for i in items]


@router.delete(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/in-charges/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Relieve a person from a sub-project",
    dependencies=[_admin_guard],
)
async def relieve_subproject_in_charge(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    user_id:       uuid.UUID,
    svc:           ProjectServiceDep,
    role_title:    str = Query(...),
) -> MessageResponse:
    await svc.relieve_subproject_in_charge(
        org_id, project_id, subproject_id, user_id, role_title
    )
    return MessageResponse(message="Sub-project in-charge relieved.")


# ── Project cover image upload ─────────────────────────────────────────────────

@router.post(
    "/{org_id}/projects/{project_id}/cover-image",
    status_code=status.HTTP_200_OK,
    summary="Upload project cover image",
    description=(
        "Upload a cover image for the project. "
        "Accepted formats: JPEG, PNG, WebP, SVG. Max 5 MB. "
        "The file is stored in MinIO and the URL is saved to OrgProject.cover_image_url. "
        "A Kafka event is published so feedback_service and stakeholder_service "
        "can sync the new cover_image_url to their ProjectCache rows. "
        "Requires MANAGER role or higher."
    ),
    responses={
        200: {"description": "Cover image uploaded — returns the new cover_image_url"},
        400: {"description": "Invalid file type or size exceeded"},
        403: {"description": "MANAGER role required"},
        404: {"description": "Project not found"},
    },
)
async def upload_project_cover_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    file:       UploadFile,
    svc:        ProjectServiceDep,
    db:         DbDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))],
) -> dict:
    """
    Upload a project cover image.

    The upload flow:
      1. ImageService validates MIME type and size.
      2. File is stored at images/projects/{project_id}/cover.{ext} in MinIO.
      3. OrgProject.cover_image_url is updated in the DB.
      4. A Kafka org_project.events message is published so subscriber services
         can update their cached cover_image_url on ProjectCache rows.
    """
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from sqlalchemy import update
    from models.org_project import OrgProject
    from events.producer import EventProducer
    from events.topics import OrgProjectEvents

    # Validate ownership
    project = await svc.get_project(org_id, project_id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found.")

    # Validate and store
    image_svc = ImageService(cfg)
    try:
        cover_url = await image_svc.upload(
            file=file,
            entity_type="projects",
            entity_id=project_id,
            slot="cover",
        )
    except ImageUploadError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc))

    # Persist to DB
    await db.execute(
        update(OrgProject)
        .where(OrgProject.id == project_id)
        .values(cover_image_url=cover_url)
    )
    await db.commit()

    # Publish Kafka event so feedback_service / stakeholder_service can sync
    producer = EventProducer()
    await producer.publish(
        topic=OrgProjectEvents.UPDATED,
        payload={
            "event":            OrgProjectEvents.UPDATED,
            "org_id":           str(org_id),
            "project_id":       str(project_id),
            "cover_image_url":  cover_url,
        },
    )

    return {"project_id": str(project_id), "cover_image_url": cover_url}


# ═════════════════════════════════════════════════════════════════════════════
# Progress Image Gallery — Projects and Sub-projects
# ═════════════════════════════════════════════════════════════════════════════
#
# Each project and sub-project has a gallery of before/during/after progress
# images. Every image carries a required title and optional description,
# location, GPS coordinates, and capture date.
#
# Routes
# ──────
#   POST   /{org_id}/projects/{project_id}/images
#   GET    /{org_id}/projects/{project_id}/images
#   GET    /{org_id}/projects/{project_id}/images/{image_id}
#   PATCH  /{org_id}/projects/{project_id}/images/{image_id}
#   DELETE /{org_id}/projects/{project_id}/images/{image_id}
#
#   POST   /{org_id}/projects/{project_id}/subprojects/{subproject_id}/images
#   GET    /{org_id}/projects/{project_id}/subprojects/{subproject_id}/images
#   GET    /{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}
#   PATCH  /{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}
#   DELETE /{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}
# ─────────────────────────────────────────────────────────────────────────────

def _img_svc(db):
    from core.config import settings as cfg
    from services.project_image_service import ProjectImageService
    return ProjectImageService(db=db, settings=cfg)


# ── Project gallery ───────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/projects/{project_id}/images",
    status_code=status.HTTP_201_CREATED,
    response_model=ProgressImageResponse,
    summary="Upload a progress image for a project",
    description=(
        "Upload a before/during/after progress image for a project. "
        "Accepted formats: JPEG, PNG, WebP. Max 5 MB. "
        "Every image requires a title. Description, phase, capture date, "
        "location, and GPS are optional but strongly recommended for "
        "World Bank progress reports and supervision missions."
    ),
)
async def upload_project_image(
    org_id:               uuid.UUID,
    project_id:           uuid.UUID,
    file:                 UploadFile = File(...),
    title:                str        = Form(...,         description="Short descriptive title (required)."),
    phase:                str        = Form("during",    description="before | during | after | other"),
    description:          str        = Form("",          description="Detailed description of the image."),
    display_order:        int        = Form(0,           description="Manual ordering within the phase gallery."),
    location_description: str        = Form("",          description="Where the photo was taken."),
    gps_lat:              float      = Form(None,        description="GPS latitude (decimal degrees)."),
    gps_lng:              float      = Form(None,        description="GPS longitude (decimal degrees)."),
    captured_at:          str        = Form(None,        description="ISO 8601 datetime when photo was taken."),
    db:                   DbDep      = ...,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> dict:
    """Upload a progress image for the project."""
    from services.image_service import ImageUploadError
    from fastapi import HTTPException
    from datetime import datetime

    from services.project_service import ProjectService
    svc = ProjectService(db=db)
    project = await svc.get_project(org_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    cap_dt = None
    if captured_at:
        try:
            cap_dt = datetime.fromisoformat(captured_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="captured_at must be ISO 8601 format.")

    try:
        result = await _img_svc(db).upload_image(
            entity_type="project",
            entity_id=project_id,
            file=file,
            title=title,
            phase=phase,
            description=description or None,
            display_order=display_order,
            location_description=location_description or None,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            captured_at=cap_dt,
            uploaded_by_user_id=membership.user_id,
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ProgressImageResponse.from_dict(result)


@router.get(
    "/{org_id}/projects/{project_id}/images",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageListResponse,
    summary="List project progress images",
    description=(
        "Returns the gallery of progress images for a project. "
        "Filter by phase to get before/during/after views. "
        "Also returns phase_counts for gallery tab headers."
    ),
)
async def list_project_images(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    phase:      Optional[str] = Query(default=None, description="before | during | after | other"),
    skip:       int           = Query(default=0, ge=0),
    limit:      int           = Query(default=50, ge=1, le=200),
    db:         DbDep         = ...,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = ...,
) -> dict:
    return ProgressImageListResponse.from_dict(await _img_svc(db).list_images("project", project_id, phase, skip, limit))


@router.get(
    "/{org_id}/projects/{project_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageResponse,
    summary="Get a single project progress image",
)
async def get_project_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    image_id:   uuid.UUID,
    db:         DbDep = ...,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = ...,
) -> dict:
    from fastapi import HTTPException
    try:
        return ProgressImageResponse.from_dict(await _img_svc(db).get_image(image_id, "project", project_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch(
    "/{org_id}/projects/{project_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageResponse,
    summary="Update project image metadata",
    description="Update title, description, phase, display_order, location, or GPS. Cannot replace the image file — delete and re-upload instead.",
)
async def update_project_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    image_id:   uuid.UUID,
    body:       Dict[str, Any],
    db:         DbDep = ...,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> dict:
    from fastapi import HTTPException
    try:
        return await _img_svc(db).update_image(image_id, "project", project_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{org_id}/projects/{project_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a project progress image",
    description=(
        "Soft-deletes the image record. The file in object storage is "
        "NEVER deleted — it is part of the project evidence trail. "
        "Requires MANAGER role."
    ),
)
async def delete_project_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    image_id:   uuid.UUID,
    db:         DbDep = ...,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> dict:
    from fastapi import HTTPException
    try:
        await _img_svc(db).delete_image(image_id, "project", project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Image {image_id} removed from gallery."}


# ── Sub-project gallery ────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images",
    status_code=status.HTTP_201_CREATED,
    response_model=ProgressImageResponse,
    summary="Upload a progress image for a sub-project",
    description=(
        "Upload a before/during/after progress image for a specific sub-project "
        "(work package). Same rules as the project-level gallery. "
        "Sub-project galleries are independent from the parent project gallery — "
        "both can coexist and are displayed separately."
    ),
)
async def upload_subproject_image(
    org_id:               uuid.UUID,
    project_id:           uuid.UUID,
    subproject_id:        uuid.UUID,
    file:                 UploadFile = File(...),
    title:                str        = Form(...,         description="Short descriptive title (required)."),
    phase:                str        = Form("during",    description="before | during | after | other"),
    description:          str        = Form("",          description="Detailed description."),
    display_order:        int        = Form(0,           description="Manual ordering within the phase gallery."),
    location_description: str        = Form("",          description="Where the photo was taken."),
    gps_lat:              float      = Form(None,        description="GPS latitude."),
    gps_lng:              float      = Form(None,        description="GPS longitude."),
    captured_at:          str        = Form(None,        description="ISO 8601 datetime when photo was taken."),
    db:                   DbDep      = ...,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> dict:
    """Upload a progress image for a sub-project."""
    from services.image_service import ImageUploadError
    from fastapi import HTTPException
    from datetime import datetime

    cap_dt = None
    if captured_at:
        try:
            cap_dt = datetime.fromisoformat(captured_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="captured_at must be ISO 8601 format.")

    try:
        result = await _img_svc(db).upload_image(
            entity_type="subproject",
            entity_id=subproject_id,
            file=file,
            title=title,
            phase=phase,
            description=description or None,
            display_order=display_order,
            location_description=location_description or None,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            captured_at=cap_dt,
            uploaded_by_user_id=membership.user_id,
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ProgressImageResponse.from_dict(result)


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageListResponse,
    summary="List sub-project progress images",
)
async def list_subproject_images(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    phase:  Optional[str] = Query(default=None, description="before | during | after | other"),
    skip:   int = Query(default=0, ge=0),
    limit:  int = Query(default=50, ge=1, le=200),
    db:     DbDep = ...,
    _:      Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = ...,
) -> dict:
    return ProgressImageListResponse.from_dict(await _img_svc(db).list_images("subproject", subproject_id, phase, skip, limit))


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageResponse,
    summary="Get a single sub-project progress image",
)
async def get_subproject_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    image_id:      uuid.UUID,
    db:            DbDep = ...,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = ...,
) -> dict:
    from fastapi import HTTPException
    try:
        return ProgressImageResponse.from_dict(await _img_svc(db).get_image(image_id, "subproject", subproject_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProgressImageResponse,
    summary="Update sub-project image metadata",
)
async def update_subproject_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    image_id:      uuid.UUID,
    body:          UpdateProgressImageRequest,
    db:            DbDep = ...,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> ProgressImageResponse:
    from fastapi import HTTPException
    try:
        return ProgressImageResponse.from_dict(await _img_svc(db).update_image(image_id, "subproject", subproject_id, body.model_dump(exclude_none=True)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a sub-project progress image",
    description="Soft-deletes the record. File in object storage is never deleted.",
)
async def delete_subproject_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    image_id:      uuid.UUID,
    db:            DbDep = ...,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = ...,
) -> dict:
    from fastapi import HTTPException
    try:
        await _img_svc(db).delete_image(image_id, "subproject", subproject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Image {image_id} removed from sub-project gallery."}


# ─────────────────────────────────────────────────────────────────────────────
# Progress Images — Project Level
# ─────────────────────────────────────────────────────────────────────────────

def _img_out(img) -> dict:
    """Serialise a ProjectProgressImage to a response dict."""
    return {
        "id":                   str(img.id),
        "project_id":           str(img.project_id) if img.project_id else None,
        "subproject_id":        str(img.subproject_id) if img.subproject_id else None,
        "image_url":            img.image_url,
        "title":                img.title,
        "description":          img.description,
        "phase":                img.phase.value if hasattr(img.phase, "value") else img.phase,
        "taken_at":             img.taken_at.isoformat() if img.taken_at else None,
        "location_description": img.location_description,
        "gps_lat":              img.gps_lat,
        "gps_lng":              img.gps_lng,
        "display_order":        img.display_order,
        "uploaded_by_user_id":  str(img.uploaded_by_user_id) if img.uploaded_by_user_id else None,
        "created_at":           img.created_at.isoformat(),
        "updated_at":           img.updated_at.isoformat(),
    }


@router.post(
    "/{org_id}/projects/{project_id}/progress-images",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a project progress image",
    description=(
        "Upload an image to document project progress. "
        "Provide a title, optional description, and phase "
        "(before / during / after). "
        "Accepted formats: JPEG, PNG, WebP. Max 10 MB. "
        "Optionally supply GPS coordinates and the date the photo was taken. "
        "Requires MANAGER role or higher."
    ),
)
async def upload_project_progress_image(
    org_id:      uuid.UUID,
    project_id:  uuid.UUID,
    file:        UploadFile,
    title:       str        = Query(..., description="Short descriptive title for the image"),
    description: str        = Query(default=None, description="Longer narrative about what the image shows"),
    phase:       str        = Query(default="during", description="before | during | after"),
    taken_at:    str        = Query(default=None, description="ISO datetime when photo was taken (optional)"),
    location_description: str = Query(default=None, description="Human-readable location e.g. 'Chainage 1+250'"),
    gps_lat:     float      = Query(default=None, description="Decimal degrees latitude"),
    gps_lng:     float      = Query(default=None, description="Decimal degrees longitude"),
    display_order: int      = Query(default=0, description="Gallery sort order within this phase"),
    svc:         ProjectServiceDep = None,
    db:          DbDep = None,
    membership:  Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from fastapi import HTTPException

    # Override max bytes for progress images (allow up to 10 MB)
    cfg_copy = type("Cfg", (), {
        **{k: getattr(cfg, k) for k in dir(cfg) if not k.startswith("_")},
        "IMAGE_MAX_BYTES": 10 * 1024 * 1024,
        "IMAGE_ALLOWED_TYPES": "image/jpeg,image/png,image/webp",
    })()

    image_svc = ImageService(cfg_copy)
    try:
        image_url = await image_svc.upload(
            file=file,
            entity_type="projects",
            entity_id=project_id,
            slot=f"progress/{uuid.uuid4()}",
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from datetime import datetime, timezone
    taken_at_dt = None
    if taken_at:
        try:
            taken_at_dt = datetime.fromisoformat(taken_at).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    img = await svc.add_project_progress_image(
        org_id=org_id,
        project_id=project_id,
        image_url=image_url,
        title=title,
        description=description,
        phase=phase,
        taken_at=taken_at_dt,
        location_description=location_description,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        display_order=display_order,
        uploaded_by=membership.user_id,
    )
    return _img_out(img)


@router.get(
    "/{org_id}/projects/{project_id}/progress-images",
    summary="List project progress images",
    description=(
        "List all progress images for a project. "
        "Filter by phase (before / during / after) to build comparison galleries."
    ),
)
async def list_project_progress_images(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    phase:      str = Query(default=None, description="before | during | after"),
    skip:       int = Query(default=0, ge=0),
    limit:      int = Query(default=100, ge=1, le=500),
    svc:        ProjectServiceDep = None,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = None,
) -> dict:
    images = await svc.list_project_progress_images(
        org_id=org_id, project_id=project_id,
        phase=phase, skip=skip, limit=limit,
    )
    return {"total": len(images), "items": [_img_out(i) for i in images]}


@router.patch(
    "/{org_id}/projects/{project_id}/progress-images/{image_id}",
    summary="Update a project progress image (title, description, phase, location, order)",
)
async def update_project_progress_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    image_id:   uuid.UUID,
    body:       Dict[str, Any],
    svc:        ProjectServiceDep = None,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    img = await svc.update_progress_image(org_id=org_id, image_id=image_id, fields=body)
    return _img_out(img)


@router.delete(
    "/{org_id}/projects/{project_id}/progress-images/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a project progress image record",
    description=(
        "Removes the DB record. The file in MinIO is retained as a permanent record. "
        "Requires MANAGER role."
    ),
)
async def delete_project_progress_image(
    org_id:     uuid.UUID,
    project_id: uuid.UUID,
    image_id:   uuid.UUID,
    svc:        ProjectServiceDep = None,
    _:          Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    await svc.delete_progress_image(org_id=org_id, image_id=image_id)
    return {"message": f"Progress image {image_id} deleted."}


# ─────────────────────────────────────────────────────────────────────────────
# Progress Images — Sub-Project Level
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/progress-images",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a sub-project progress image",
    description=(
        "Upload an image documenting progress on a specific work package / sub-project. "
        "Provide a title, optional description, and phase (before / during / after). "
        "Accepted formats: JPEG, PNG, WebP. Max 10 MB. "
        "Requires MANAGER role or higher."
    ),
)
async def upload_subproject_progress_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    file:          UploadFile,
    title:         str   = Query(...),
    description:   str   = Query(default=None),
    phase:         str   = Query(default="during", description="before | during | after"),
    taken_at:      str   = Query(default=None),
    location_description: str = Query(default=None),
    gps_lat:       float = Query(default=None),
    gps_lng:       float = Query(default=None),
    display_order: int   = Query(default=0),
    svc:           ProjectServiceDep = None,
    db:            DbDep = None,
    membership:    Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from fastapi import HTTPException

    cfg_copy = type("Cfg", (), {
        **{k: getattr(cfg, k) for k in dir(cfg) if not k.startswith("_")},
        "IMAGE_MAX_BYTES": 10 * 1024 * 1024,
        "IMAGE_ALLOWED_TYPES": "image/jpeg,image/png,image/webp",
    })()

    image_svc = ImageService(cfg_copy)
    try:
        image_url = await image_svc.upload(
            file=file,
            entity_type="subprojects",
            entity_id=subproject_id,
            slot=f"progress/{uuid.uuid4()}",
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from datetime import datetime, timezone
    taken_at_dt = None
    if taken_at:
        try:
            taken_at_dt = datetime.fromisoformat(taken_at).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    img = await svc.add_subproject_progress_image(
        org_id=org_id,
        project_id=project_id,
        subproject_id=subproject_id,
        image_url=image_url,
        title=title,
        description=description,
        phase=phase,
        taken_at=taken_at_dt,
        location_description=location_description,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        display_order=display_order,
        uploaded_by=membership.user_id,
    )
    return _img_out(img)


@router.get(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/progress-images",
    summary="List sub-project progress images",
)
async def list_subproject_progress_images(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    phase:         str = Query(default=None, description="before | during | after"),
    skip:          int = Query(default=0, ge=0),
    limit:         int = Query(default=100, ge=1, le=500),
    svc:           ProjectServiceDep = None,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MEMBER))] = None,
) -> dict:
    images = await svc.list_subproject_progress_images(
        org_id=org_id, project_id=project_id,
        subproject_id=subproject_id,
        phase=phase, skip=skip, limit=limit,
    )
    return {"total": len(images), "items": [_img_out(i) for i in images]}


@router.patch(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/progress-images/{image_id}",
    summary="Update a sub-project progress image",
)
async def update_subproject_progress_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    image_id:      uuid.UUID,
    body:          Dict[str, Any],
    svc:           ProjectServiceDep = None,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    img = await svc.update_progress_image(org_id=org_id, image_id=image_id, fields=body)
    return _img_out(img)


@router.delete(
    "/{org_id}/projects/{project_id}/subprojects/{subproject_id}/progress-images/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a sub-project progress image record",
)
async def delete_subproject_progress_image(
    org_id:        uuid.UUID,
    project_id:    uuid.UUID,
    subproject_id: uuid.UUID,
    image_id:      uuid.UUID,
    svc:           ProjectServiceDep = None,
    _:             Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))] = None,
) -> dict:
    await svc.delete_progress_image(org_id=org_id, image_id=image_id)
    return {"message": f"Progress image {image_id} deleted."}
