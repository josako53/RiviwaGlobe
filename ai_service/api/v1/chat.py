"""api/v1/chat.py — Web/mobile AI conversation endpoints."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, OptTokenDep
from schemas.conversation import StartConversation, SendMessage, ConversationResponse, ConversationDetail
from services.conversation_service import ConversationService

router = APIRouter(prefix="/ai", tags=["AI Conversation"])


def _svc(db) -> ConversationService:
    return ConversationService(db=db)


def _conv_response(conv, reply: str, submitted: bool = False, submitted_feedback=None) -> dict:
    extracted = conv.get_extracted()
    fb_list   = [
        {
            "feedback_id":   f.get("feedback_id", ""),
            "unique_ref":    f.get("unique_ref", ""),
            "feedback_type": f.get("feedback_type", ""),
        }
        for f in (submitted_feedback or [])
    ]
    return {
        "conversation_id":   str(conv.id),
        "reply":             reply,
        "status":            conv.status.value,
        "stage":             conv.stage.value,
        "turn_count":        conv.turn_count,
        "confidence":        float(extracted.get("confidence", 0.0)),
        "language":          conv.language,
        "submitted":         submitted,
        "submitted_feedback": fb_list,
        "project_name":      conv.project_name,
        "is_urgent":         conv.is_urgent,
        "incharge_name":     conv.incharge_name,
        "incharge_phone":    conv.incharge_phone,
    }


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    summary="Start a new AI conversation",
    description=(
        "Start a new Riviwa AI AI conversation for submitting grievances, suggestions, or applause. "
        "No authentication required for anonymous web/mobile Consumers. "
        "Pass user_id from JWT for registered Consumers (auto-identifies them)."
    ),
)
async def start_conversation(body: StartConversation, db: DbDep, token: OptTokenDep) -> dict:
    user_id = token.sub if token else body.user_id
    conv, reply = await _svc(db).start_conversation(
        channel    = body.channel,
        language   = body.language,
        project_id = body.project_id,
        user_id    = user_id,
        web_token  = body.web_token,
    )
    return _conv_response(conv, reply)


@router.post(
    "/conversations/{conversation_id}/message",
    summary="Send a message in an AI conversation",
    description=(
        "Send the Consumer's message to Riviwa AI. The AI responds, extracts feedback fields, "
        "and auto-submits when confidence ≥ 0.82. "
        "Supports Swahili and English — Riviwa AI auto-detects the language."
    ),
)
async def send_message(conversation_id: uuid.UUID, body: SendMessage, db: DbDep) -> dict:
    conv, reply, submitted, feedback_list = await _svc(db).process_message(
        conversation_id = conversation_id,
        message         = body.message,
        media_urls      = body.media_urls,
    )
    return _conv_response(conv, reply, submitted, feedback_list)


@router.get(
    "/conversations/{conversation_id}",
    summary="Get AI conversation status and transcript",
)
async def get_conversation(conversation_id: uuid.UUID, db: DbDep) -> dict:
    from repositories.conversation_repo import ConversationRepository
    repo = ConversationRepository(db)
    conv = await repo.get_or_404(conversation_id)
    extracted = conv.get_extracted()
    return {
        "conversation_id": str(conv.id),
        "channel":         conv.channel.value,
        "status":          conv.status.value,
        "stage":           conv.stage.value,
        "language":        conv.language,
        "turn_count":      conv.turn_count,
        "confidence":      float(extracted.get("confidence", 0.0)),
        "is_registered":   conv.is_registered,
        "submitter_name":  conv.submitter_name,
        "project_id":      str(conv.project_id) if conv.project_id else None,
        "project_name":    conv.project_name,
        "extracted_data":  extracted,
        "submitted_feedback": conv.get_submitted(),
        "transcript":      conv.get_turns(),
        "is_urgent":       conv.is_urgent,
        "incharge_name":   conv.incharge_name,
        "incharge_phone":  conv.incharge_phone,
        "started_at":      conv.started_at.isoformat(),
        "last_active_at":  conv.last_active_at.isoformat(),
        "completed_at":    conv.completed_at.isoformat() if conv.completed_at else None,
    }
