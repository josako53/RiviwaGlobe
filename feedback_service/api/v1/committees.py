"""api/v1/committees.py — GRM Committee management endpoints."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, StaffDep
from schemas.committee import AddCommitteeMember, CreateCommittee, UpdateCommittee
from services.committee_service import CommitteeService
from api.v1.serialisers import committee_out, member_out

router = APIRouter(prefix="/committees", tags=["GRM Committees"])
def _svc(db): return CommitteeService(db=db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a Grievance Handling Committee (GHC)",
    description=(
        "Create a new GHC that will handle grievances at a specific GRM level. "
        "Each committee operates within an LGA jurisdiction and is linked to a project. "
        "After creating, add members via POST /committees/{id}/members."
    ),
)
async def create_committee(body: CreateCommittee, db: DbDep, _: StaffDep) -> dict:
    return committee_out(await _svc(db).create(body.model_dump(exclude_none=True)))


@router.get("", summary="List GHCs")
async def list_committees(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None, description="Filter by project"),
    level: Optional[str] = Query(default=None, description="Filter by GRM level: ward, lga_grm_unit, coordinating_unit, tarura_wbcu, tanroads"),
    lga: Optional[str] = Query(default=None, description="Filter by LGA jurisdiction"),
    org_sub_project_id: Optional[uuid.UUID] = Query(default=None, description="Filter by sub-project"),
    stakeholder_id: Optional[uuid.UUID] = Query(default=None, description="Filter by covered stakeholder group"),
    active_only: bool = Query(default=True, description="Only return active committees"),
) -> dict:
    items = await _svc(db).list(
        project_id=project_id, level=level, lga=lga,
        org_sub_project_id=org_sub_project_id, stakeholder_id=stakeholder_id, active_only=active_only,
    )
    return {"items": [committee_out(c) for c in items]}


@router.patch(
    "/{committee_id}",
    summary="Update committee details",
    description="Update an existing GHC. Only include fields you want to change.",
)
async def update_committee(committee_id: uuid.UUID, body: UpdateCommittee, db: DbDep, _: StaffDep) -> dict:
    return committee_out(await _svc(db).update(committee_id, body.model_dump(exclude_none=True)))


@router.post(
    "/{committee_id}/stakeholders/{stakeholder_id}",
    status_code=status.HTTP_200_OK,
    summary="Add a stakeholder group to this committee's coverage",
    description="Link a stakeholder group to this GHC so grievances from that group are routed here.",
)
async def add_stakeholder(committee_id: uuid.UUID, stakeholder_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return committee_out(await _svc(db).add_stakeholder(committee_id, stakeholder_id))


@router.delete(
    "/{committee_id}/stakeholders/{stakeholder_id}",
    summary="Remove a stakeholder group from this committee's coverage",
)
async def remove_stakeholder(committee_id: uuid.UUID, stakeholder_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return committee_out(await _svc(db).remove_stakeholder(committee_id, stakeholder_id))


@router.post(
    "/{committee_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Add member to GHC",
    description=(
        "Add a user to the committee with a specific role. "
        "Roles: chairperson (leads), secretary (records & coordinates), member (regular)."
    ),
)
async def add_member(committee_id: uuid.UUID, body: AddCommitteeMember, db: DbDep, _: StaffDep) -> dict:
    return member_out(await _svc(db).add_member(committee_id, body.model_dump()))


@router.delete(
    "/{committee_id}/members/{user_id}",
    summary="Remove member from GHC",
)
async def remove_member(committee_id: uuid.UUID, user_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    await _svc(db).remove_member(committee_id, user_id)
    return {"message": f"Member {user_id} removed from committee {committee_id}."}
