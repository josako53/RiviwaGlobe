"""api/v1/feedback.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, KafkaDep, StaffDep, OptTokenDep
from services.feedback_service import FeedbackService
from api.v1.serialisers import feedback_out, action_out, esc_out, resolution_out, appeal_out

router = APIRouter(prefix="/feedback", tags=["Feedback"])
def _svc(db, kafka): return FeedbackService(db=db, producer=kafka)

@router.post("", status_code=status.HTTP_201_CREATED, summary="Submit feedback (grievance / suggestion / applause)")
async def submit_feedback(body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: OptTokenDep) -> dict:
    return feedback_out(await _svc(db, kafka).submit(body, token_sub=token.sub if token else None))

@router.get("", summary="List feedback records [staff]")
async def list_feedback(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    current_level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    lga: Optional[str] = Query(default=None),
    is_anonymous: Optional[bool] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    submitted_by_stakeholder_id: Optional[uuid.UUID] = Query(default=None),
    assigned_committee_id: Optional[uuid.UUID] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list(
        project_id=project_id, feedback_type=feedback_type, status=status_,
        priority=priority, current_level=current_level, category=category, lga=lga,
        is_anonymous=is_anonymous, submission_method=submission_method, channel=channel,
        submitted_by_stakeholder_id=submitted_by_stakeholder_id,
        assigned_committee_id=assigned_committee_id, skip=skip, limit=limit,
    )
    return {"items": [feedback_out(f) for f in items], "count": len(items)}

@router.get("/{feedback_id}", summary="Feedback detail with full history")
async def get_feedback(feedback_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    f = await _svc(db, kafka).get_with_history_or_404(feedback_id)
    return {
        **feedback_out(f),
        "actions":     [action_out(a) for a in sorted(f.actions, key=lambda x: x.performed_at)],
        "escalations": [esc_out(e) for e in sorted(f.escalations, key=lambda x: x.escalated_at)],
        "resolution":  resolution_out(f.resolution) if f.resolution else None,
        "appeal":      appeal_out(f.appeal) if f.appeal else None,
    }

@router.patch("/{feedback_id}/acknowledge", summary="Acknowledge receipt")
async def acknowledge_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).acknowledge(feedback_id, body, by=token.sub))

@router.patch("/{feedback_id}/assign", summary="Assign to staff member or committee")
async def assign_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).assign(feedback_id, body, by=token.sub))

@router.post("/{feedback_id}/escalate", status_code=status.HTTP_200_OK, summary="Escalate to next GRM level")
async def escalate_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).escalate(feedback_id, body, by=token.sub))

@router.post("/{feedback_id}/resolve", status_code=status.HTTP_200_OK, summary="Record resolution")
async def resolve_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).resolve(feedback_id, body, by=token.sub))

@router.post("/{feedback_id}/appeal", status_code=status.HTTP_200_OK, summary="File appeal against resolution")
async def file_appeal(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).appeal(feedback_id, body, by=token.sub))

@router.patch("/{feedback_id}/close", summary="Close feedback [final state]")
async def close_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).close(feedback_id, body, by=token.sub))

@router.patch("/{feedback_id}/dismiss", summary="Dismiss feedback")
async def dismiss_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).dismiss(feedback_id, body, by=token.sub))
