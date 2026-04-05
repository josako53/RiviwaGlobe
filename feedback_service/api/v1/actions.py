"""api/v1/actions.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict
from fastapi import APIRouter, status
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.feedback_service import FeedbackService
from api.v1.serialisers import action_out

router = APIRouter(prefix="/feedback", tags=["Actions"])
def _svc(db, kafka): return FeedbackService(db=db, producer=kafka)

@router.post("/{feedback_id}/actions", status_code=status.HTTP_201_CREATED, summary="Log an action")
async def log_action(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return action_out(await _svc(db, kafka).log_action(feedback_id, body, by=token.sub))

@router.get("/{feedback_id}/actions", summary="Get action log for a feedback item")
async def list_actions(feedback_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return {"items": [action_out(a) for a in await _svc(db, kafka).list_actions(feedback_id)]}
