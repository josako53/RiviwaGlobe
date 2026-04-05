"""api/v1/contacts.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.stakeholder_service import StakeholderService

router = APIRouter(prefix="/stakeholders", tags=["Contacts"])

def _svc(db, kafka): return StakeholderService(db=db, producer=kafka)
def _c_out(c): return {"id":str(c.id),"stakeholder_id":str(c.stakeholder_id),"user_id":str(c.user_id) if c.user_id else None,"full_name":c.full_name,"title":c.title,"role_in_org":c.role_in_org,"email":c.email,"phone":c.phone,"preferred_channel":c.preferred_channel,"is_primary":c.is_primary,"can_submit_feedback":c.can_submit_feedback,"can_receive_communications":c.can_receive_communications,"can_distribute_communications":c.can_distribute_communications,"is_active":c.is_active,"notes":c.notes,"created_at":c.created_at.isoformat()}

@router.post("/{stakeholder_id}/contacts", status_code=status.HTTP_201_CREATED, summary="Add a contact to a stakeholder")
async def add_contact(stakeholder_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _c_out(await _svc(db, kafka).add_contact(stakeholder_id, body))

@router.get("/{stakeholder_id}/contacts", summary="List contacts for a stakeholder")
async def list_contacts(stakeholder_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep, active_only: bool = Query(default=True)) -> dict:
    return {"items": [_c_out(c) for c in await _svc(db, kafka).list_contacts(stakeholder_id, active_only)]}

@router.patch("/{stakeholder_id}/contacts/{contact_id}", summary="Update a contact")
async def update_contact(stakeholder_id: uuid.UUID, contact_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _c_out(await _svc(db, kafka).update_contact(stakeholder_id, contact_id, body))

@router.delete("/{stakeholder_id}/contacts/{contact_id}", summary="Deactivate a contact")
async def deactivate_contact(stakeholder_id: uuid.UUID, contact_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    await _svc(db, kafka).deactivate_contact(stakeholder_id, contact_id, body.get("reason"))
    return {"message": f"Contact {contact_id} deactivated."}
