"""api/v1/communications.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.communication_service import CommunicationService

router = APIRouter(prefix="/communications", tags=["Communications"])

def _svc(db, kafka): return CommunicationService(db=db, producer=kafka)
def _c_out(c): return {"id":str(c.id),"project_id":str(c.project_id),"stakeholder_id":str(c.stakeholder_id) if c.stakeholder_id else None,"contact_id":str(c.contact_id) if c.contact_id else None,"channel":c.channel,"direction":c.direction,"purpose":c.purpose,"subject":c.subject,"content_summary":c.content_summary,"document_urls":c.document_urls,"in_response_to_id":str(c.in_response_to_id) if c.in_response_to_id else None,"distribution_required":c.distribution_required,"distribution_deadline":c.distribution_deadline.isoformat() if c.distribution_deadline else None,"sent_at":c.sent_at.isoformat() if c.sent_at else None,"received_at":c.received_at.isoformat() if c.received_at else None,"acknowledged_at":c.acknowledged_at.isoformat() if c.acknowledged_at else None,"created_at":c.created_at.isoformat()}
def _d_out(d): return {"id":str(d.id),"communication_id":str(d.communication_id),"contact_id":str(d.contact_id),"distributed_to_count":d.distributed_to_count,"distribution_method":d.distribution_method,"distribution_notes":d.distribution_notes,"distributed_at":d.distributed_at.isoformat() if d.distributed_at else None,"concerns_raised_after":d.concerns_raised_after,"feedback_ref_id":str(d.feedback_ref_id) if d.feedback_ref_id else None,"acknowledged_at":d.acknowledged_at.isoformat() if d.acknowledged_at else None,"has_pending_concerns":d.has_pending_concerns(),"created_at":d.created_at.isoformat()}

@router.post("", status_code=status.HTTP_201_CREATED, summary="Log a communication record")
async def log_communication(body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _c_out(await _svc(db, kafka).log_communication(body, sent_by=token.sub))

@router.get("", summary="List communication records")
async def list_communications(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stakeholder_id: Optional[uuid.UUID] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list_communications(project_id=project_id, stakeholder_id=stakeholder_id, direction=direction, channel=channel, skip=skip, limit=limit)
    return {"items": [_c_out(c) for c in items]}

@router.get("/{comm_id}", summary="Communication detail with distributions")
async def get_communication(comm_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    c, dists = await _svc(db, kafka).get_communication_with_distributions(comm_id)
    return {**_c_out(c), "distributions": [_d_out(d) for d in dists]}

@router.post("/{comm_id}/distributions", status_code=status.HTTP_201_CREATED, summary="Log that a contact distributed this communication")
async def log_distribution(comm_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _d_out(await _svc(db, kafka).log_distribution(comm_id, body, logged_by=token.sub))

@router.patch("/{comm_id}/distributions/{dist_id}", summary="Update distribution record (confirm, add concerns, link feedback)")
async def update_distribution(comm_id: uuid.UUID, dist_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _d_out(await _svc(db, kafka).update_distribution(comm_id, dist_id, body, updated_by=token.sub))
