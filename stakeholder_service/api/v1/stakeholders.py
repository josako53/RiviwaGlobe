# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  stakeholder_service  |  Port: 8070  |  DB: stakeholder_db (5436)
# FILE     :  api/v1/stakeholders.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/stakeholders.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from core.dependencies import DbDep, KafkaDep, StaffDep, require_platform_role
from models.stakeholder import ImportanceRating
from schemas.stakeholder import RegisterStakeholder, UpdateStakeholder, RegisterStakeholderProject
from services.stakeholder_service import StakeholderService


def _extract_jwt(request: Request) -> Optional[str]:
    """Extract raw JWT string from the Authorization: Bearer header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None

router = APIRouter(prefix="/stakeholders", tags=["Stakeholders"])

def _svc(db, kafka): return StakeholderService(db=db, producer=kafka)

def _s_out(s): return {"id":str(s.id),"stakeholder_type":s.stakeholder_type,"entity_type":s.entity_type,"category":s.category,"affectedness":s.affectedness,"importance_rating":s.importance_rating,"display_name":s.display_name,"org_name":s.org_name,"first_name":s.first_name,"last_name":s.last_name,"org_id":str(s.org_id) if s.org_id else None,"address_id":str(s.address_id) if s.address_id else None,"lga":s.lga,"ward":s.ward,"language_preference":s.language_preference,"preferred_channel":s.preferred_channel,"needs_translation":s.needs_translation,"needs_transport":s.needs_transport,"needs_childcare":s.needs_childcare,"is_vulnerable":s.is_vulnerable,"vulnerable_group_types":s.vulnerable_group_types,"participation_barriers":s.participation_barriers,"notes":s.notes,"created_at":s.created_at.isoformat()}
def _c_brief(c): return {"id":str(c.id),"full_name":c.full_name,"title":c.title,"role_in_org":c.role_in_org,"email":c.email,"phone":c.phone,"preferred_channel":c.preferred_channel,"is_primary":c.is_primary,"can_submit_feedback":c.can_submit_feedback,"can_receive_communications":c.can_receive_communications,"can_distribute_communications":c.can_distribute_communications,"user_id":str(c.user_id) if c.user_id else None,"is_active":c.is_active}
def _sp_out(sp): return {"id":str(sp.id),"stakeholder_id":str(sp.stakeholder_id),"project_id":str(sp.project_id),"is_consumer":sp.is_consumer,"affectedness":sp.affectedness,"impact_description":sp.impact_description,"consultation_count":sp.consultation_count,"registered_at":sp.registered_at.isoformat()}
def _eng_out(e): return {"id":str(e.id),"contact_id":str(e.contact_id),"activity_id":str(e.activity_id),"attendance_status":e.attendance_status,"concerns_raised":e.concerns_raised,"response_given":e.response_given,"feedback_submitted":e.feedback_submitted,"feedback_ref_id":str(e.feedback_ref_id) if e.feedback_ref_id else None,"created_at":e.created_at.isoformat()}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Register a stakeholder")
async def register_stakeholder(body: RegisterStakeholder, request: Request, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _s_out(await _svc(db, kafka).register(body.model_dump(exclude_none=True), registered_by=token.sub, jwt_token=_extract_jwt(request)))


@router.get("", summary="List stakeholders with optional filters")
async def list_stakeholders(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    stakeholder_type: Optional[str]            = Query(default=None, description="Filter by stakeholder type (consumer / interested_party / implementing_agency / local_authority / civil_society / media / private_sector / government / international_org)"),
    category:         Optional[str]            = Query(default=None, description="Filter by stakeholder category"),
    lga:              Optional[str]            = Query(default=None, description="Filter by Local Government Authority (partial match)"),
    affectedness:     Optional[str]            = Query(default=None, description="Filter by affectedness level (directly_affected / indirectly_affected / not_affected)"),
    is_vulnerable:    Optional[bool]           = Query(default=None, description="Filter to vulnerable stakeholders only"),
    importance:       Optional[ImportanceRating] = Query(default=None, description="Filter by importance rating in any stage (high / medium / low). Requires project_id or stage_id."),
    project_id:       Optional[uuid.UUID]      = Query(default=None, description="Filter to stakeholders registered under a specific project"),
    stage_id:         Optional[uuid.UUID]      = Query(default=None, description="Filter to stakeholders with a stage engagement in this specific stage"),
    skip:             int                      = Query(default=0, ge=0),
    limit:            int                      = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list(
        stakeholder_type=stakeholder_type, category=category,
        lga=lga, affectedness=affectedness, is_vulnerable=is_vulnerable,
        importance=importance, project_id=project_id, stage_id=stage_id,
        skip=skip, limit=limit,
    )
    return {"items": [_s_out(s) for s in items], "count": len(items)}


@router.get("/analysis", summary="Stakeholder analysis matrix (Annex 3 / SEP format)")
async def stakeholder_analysis(
    db:           DbDep,
    kafka:        KafkaDep,
    _:            StaffDep,
    project_id:   uuid.UUID               = Query(..., description="Project to analyse (required)"),
    stage_id:     Optional[uuid.UUID]     = Query(default=None, description="Narrow to a specific project stage"),
    importance:   Optional[ImportanceRating] = Query(default=None, description="Filter by importance rating (high / medium / low)"),
    category:     Optional[str]           = Query(default=None, description="Filter by stakeholder category"),
    affectedness: Optional[str]           = Query(default=None, description="Filter by affectedness level"),
    is_vulnerable: Optional[bool]         = Query(default=None, description="Show vulnerable stakeholders only"),
    skip:         int                     = Query(default=0, ge=0),
    limit:        int                     = Query(default=200, ge=1, le=500),
) -> dict:
    """
    Returns the full Stakeholder Analysis matrix in Annex 3 / SEP format.

    Each row represents one stakeholder × stage combination and includes:
    - **why_important** (role_in_stage) — Why this stakeholder matters to this stage
    - **interests** — What they want to achieve / are concerned about
    - **potential_risks** — Risks they pose or face
    - **how_to_engage** — Recommended engagement approach
    - **when_to_engage** (engagement_frequency) — Timing and frequency
    - **importance** — HIGH / MEDIUM / LOW with justification

    Filterable by: project, stage, importance, category, affectedness,
    vulnerability. Use stage_id for a per-stage Annex 3 table.
    Use no stage_id for the full project-wide matrix.
    """
    rows = await _svc(db, kafka).stakeholder_analysis(
        project_id=project_id, stage_id=stage_id, importance=importance,
        category=category, affectedness=affectedness, is_vulnerable=is_vulnerable,
        skip=skip, limit=limit,
    )
    return {
        "project_id": str(project_id),
        "stage_id":   str(stage_id) if stage_id else None,
        "filters":    {
            "importance":   importance,
            "category":     category,
            "affectedness": affectedness,
            "is_vulnerable": is_vulnerable,
        },
        "count": len(rows),
        "items": rows,
    }


@router.get("/{stakeholder_id}", summary="Stakeholder detail with contacts")
async def get_stakeholder(stakeholder_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    s = await _svc(db, kafka).get_with_contacts_or_404(stakeholder_id)
    return {**_s_out(s), "contacts": [_c_brief(c) for c in s.contacts]}


@router.patch("/{stakeholder_id}", summary="Update stakeholder profile")
async def update_stakeholder(stakeholder_id: uuid.UUID, body: UpdateStakeholder, request: Request, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _s_out(await _svc(db, kafka).update(stakeholder_id, body.model_dump(exclude_none=True), jwt_token=_extract_jwt(request)))


@router.delete("/{stakeholder_id}", status_code=status.HTTP_200_OK, summary="Soft-delete a stakeholder [admin]", dependencies=[Depends(require_platform_role("admin"))])
async def delete_stakeholder(stakeholder_id: uuid.UUID, db: DbDep, kafka: KafkaDep) -> dict:
    await _svc(db, kafka).delete(stakeholder_id)
    return {"message": f"Stakeholder {stakeholder_id} deactivated."}


@router.post("/{stakeholder_id}/projects", status_code=status.HTTP_201_CREATED, summary="Register stakeholder under a project")
async def register_for_project(stakeholder_id: uuid.UUID, body: RegisterStakeholderProject, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _sp_out(await _svc(db, kafka).register_for_project(stakeholder_id, body.model_dump(exclude_none=True), registered_by=token.sub))


@router.get("/{stakeholder_id}/projects", summary="List project registrations for a stakeholder")
async def list_stakeholder_projects(stakeholder_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return {"items": [_sp_out(sp) for sp in await _svc(db, kafka).list_projects(stakeholder_id)]}


@router.get("/{stakeholder_id}/engagements", summary="Engagement history for a stakeholder")
async def stakeholder_engagements(stakeholder_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return {"items": [_eng_out(e) for e in await _svc(db, kafka).engagement_history(stakeholder_id)]}

