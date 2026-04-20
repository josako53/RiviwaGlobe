# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/departments.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/departments.py
═══════════════════════════════════════════════════════════════════════════════
Department management under an organisation.

Routes
──────
  POST   /orgs/{org_id}/departments                    Create department [admin+]
  GET    /orgs/{org_id}/departments                    List departments
  GET    /orgs/{org_id}/departments/{dept_id}          Get department
  PATCH  /orgs/{org_id}/departments/{dept_id}          Update [admin+]
  DELETE /orgs/{org_id}/departments/{dept_id}          Deactivate [admin+]

Scoping
───────
  All endpoints are scoped to an org.  The authenticated user must be an
  active member of that org (any role) to read; ADMIN or OWNER to mutate.

  GET accepts an optional ?branch_id= query param to filter to departments
  visible at a specific branch (branch-scoped + org-wide).
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from core.dependencies import require_org_role
from models.organisation import OrgMemberRole
from api.v1.deps import DbDep, PublisherDep
from events.publisher import EventPublisher
from schemas.department import CreateDepartment, DepartmentOut, UpdateDepartment
from services.department_service import DepartmentService

router = APIRouter(prefix="/orgs", tags=["Departments"])


def _svc(db, publisher: EventPublisher) -> DepartmentService:
    return DepartmentService(db=db, publisher=publisher)


def _out(d) -> dict:
    return {
        "id":          str(d.id),
        "org_id":      str(d.org_id),
        "branch_id":   str(d.branch_id) if d.branch_id else None,
        "name":        d.name,
        "code":        d.code,
        "description": d.description,
        "sort_order":  d.sort_order,
        "is_active":   d.is_active,
        "created_at":  d.created_at.isoformat(),
        "updated_at":  d.updated_at.isoformat(),
    }


@router.post(
    "/{org_id}/departments",
    status_code=status.HTTP_201_CREATED,
    summary="Create a department [admin+]",
)
async def create_department(
    org_id: uuid.UUID,
    body: CreateDepartment,
    db: DbDep,
    publisher: PublisherDep,
    member=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    dept = await _svc(db, publisher).create(
        org_id=org_id,
        data=body.model_dump(exclude_none=True),
        created_by=member.user_id,
    )
    return _out(dept)


@router.get(
    "/{org_id}/departments",
    summary="List departments for an organisation",
)
async def list_departments(
    org_id:    uuid.UUID,
    db:        DbDep,
    publisher: PublisherDep,
    branch_id:   Optional[uuid.UUID] = Query(default=None, description="Filter to a specific branch (includes org-wide departments)"),
    active_only: bool                = Query(default=True,  description="Include only active departments"),
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    items = await _svc(db, publisher).list(
        org_id=org_id, branch_id=branch_id, active_only=active_only
    )
    return {"items": [_out(d) for d in items], "count": len(items)}


@router.get(
    "/{org_id}/departments/{dept_id}",
    summary="Get a department",
)
async def get_department(
    org_id:  uuid.UUID,
    dept_id: uuid.UUID,
    db:      DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    return _out(await _svc(db, publisher).get(dept_id=dept_id, org_id=org_id))


@router.patch(
    "/{org_id}/departments/{dept_id}",
    summary="Update a department [admin+]",
)
async def update_department(
    org_id:  uuid.UUID,
    dept_id: uuid.UUID,
    body:    UpdateDepartment,
    db:      DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    return _out(
        await _svc(db, publisher).update(
            dept_id=dept_id,
            org_id=org_id,
            data=body.model_dump(exclude_unset=True),
        )
    )


@router.delete(
    "/{org_id}/departments/{dept_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a department [admin+]",
)
async def deactivate_department(
    org_id:  uuid.UUID,
    dept_id: uuid.UUID,
    db:      DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    return _out(await _svc(db, publisher).deactivate(dept_id=dept_id, org_id=org_id))
