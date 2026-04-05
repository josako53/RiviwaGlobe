"""api/v1/focal_persons.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.communication_service import CommunicationService

router = APIRouter(prefix="/focal-persons", tags=["Focal Persons"])

def _svc(db, kafka): return CommunicationService(db=db, producer=kafka)
def _fp_out(fp): return {"id":str(fp.id),"project_id":str(fp.project_id),"org_type":fp.org_type,"organization_name":fp.organization_name,"title":fp.title,"full_name":fp.full_name,"phone":fp.phone,"email":fp.email,"address":fp.address,"lga":fp.lga,"subproject":fp.subproject,"user_id":str(fp.user_id) if fp.user_id else None,"is_active":fp.is_active,"notes":fp.notes,"created_at":fp.created_at.isoformat()}

@router.post("", status_code=status.HTTP_201_CREATED, summary="Register a focal person (SEP Table 9)")
async def create_focal_person(body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _fp_out(await _svc(db, kafka).create_focal_person(body))

@router.get("", summary="List focal persons")
async def list_focal_persons(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    org_type: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
) -> dict:
    return {"items": [_fp_out(fp) for fp in await _svc(db, kafka).list_focal_persons(project_id=project_id, org_type=org_type, active_only=active_only)]}

@router.patch("/{fp_id}", summary="Update focal person details")
async def update_focal_person(fp_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _fp_out(await _svc(db, kafka).update_focal_person(fp_id, body))
