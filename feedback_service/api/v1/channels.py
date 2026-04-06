"""api/v1/channels.py — Two-way AI conversation channels + staff management."""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, Request, status
from core.dependencies import DbDep, StaffDep, OptTokenDep
from schemas.feedback import AIChannelSessionCreate, AIChannelMessage, AISessionResponse
from services.channel_service import ChannelService
from api.v1.serialisers import session_out

router = APIRouter(tags=["Channel Sessions"])
def _svc(db): return ChannelService(db=db)


# ═════════════════════════════════════════════════════════════════════════════
# AI-POWERED CHANNELS — No staff intervention required
# PAP interacts directly with the Riviwa AI assistant via SMS/WhatsApp/Call.
# The LLM collects all feedback details through multi-turn conversation
# and auto-submits when confidence >= 0.80.
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/ai/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=AISessionResponse,
    summary="Start an AI-powered feedback conversation",
    description=(
        "Start a new AI conversation session via SMS, WhatsApp, or phone call. "
        "The Riviwa AI assistant will guide the PAP through submitting a grievance, "
        "suggestion, or applause — no staff intervention needed. "
        "The LLM automatically extracts feedback details and auto-submits when confident."
    ),
    tags=["AI Channels"],
)
async def ai_start_session(body: AIChannelSessionCreate, db: DbDep) -> AISessionResponse:
    """No auth required — PAPs interact via phone number/WhatsApp ID."""
    session = await _svc(db).create_session(
        data=body.model_dump(exclude_none=True),
        created_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system user
    )
    return AISessionResponse(
        session_id=session.id,
        reply=session.get_turns()[-1]["content"] if session.get_turns() else "",
        submitted=False,
        status=session.status.value,
        turn_count=session.turn_count,
        confidence=0.0,
        language=session.language,
    )


@router.post(
    "/ai/sessions/{session_id}/message",
    response_model=AISessionResponse,
    summary="Send a message in an AI conversation",
    description=(
        "Send the PAP's message to the AI assistant. The LLM responds, extracts "
        "feedback details (type, description, location, etc.), and auto-submits "
        "the feedback when it has enough information (confidence >= 0.80). "
        "Supports Kiswahili and English — the AI detects and responds in the user's language."
    ),
    tags=["AI Channels"],
)
async def ai_send_message(session_id: uuid.UUID, body: AIChannelMessage, db: DbDep) -> AISessionResponse:
    """No auth required — identified by session_id."""
    result = await _svc(db).process_message(session_id, body.message)
    session = await _svc(db).get_or_404(session_id)
    extracted = session.extracted_data or {}
    return AISessionResponse(
        session_id=session_id,
        reply=result["reply"],
        submitted=result.get("submitted", False),
        feedback_id=uuid.UUID(result["feedback_id"]) if result.get("feedback_id") else None,
        unique_ref=None,
        status=result["status"],
        turn_count=result["turn_count"],
        confidence=float(extracted.get("confidence", 0.0)),
        language=extracted.get("language", session.language or "sw"),
    )


@router.get(
    "/ai/sessions/{session_id}",
    summary="Get AI session status and transcript",
    tags=["AI Channels"],
)
async def ai_get_session(session_id: uuid.UUID, db: DbDep) -> dict:
    """Check session status, extracted data, and conversation history."""
    s = await _svc(db).get_or_404(session_id)
    extracted = s.extracted_data or {}
    return {
        "session_id": str(s.id),
        "status": s.status.value,
        "channel": s.channel.value,
        "language": s.language,
        "turn_count": s.turn_count,
        "confidence": float(extracted.get("confidence", 0.0)),
        "extracted_data": extracted,
        "feedback_id": str(s.feedback_id) if s.feedback_id else None,
        "transcript": s.get_turns(),
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


# ═════════════════════════════════════════════════════════════════════════════
# STAFF-MANAGED SESSIONS — Staff initiates/monitors on behalf of PAP
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/channel-sessions", status_code=status.HTTP_201_CREATED,
             summary="Start a staff-managed channel session", tags=["Staff Channel Management"])
async def create_session(body: Dict[str, Any], db: DbDep, token: StaffDep) -> dict:
    return session_out(await _svc(db).create_session(body, created_by=token.sub))

@router.get("/channel-sessions", summary="List channel sessions", tags=["Staff Channel Management"])
async def list_sessions(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db).list(project_id=project_id, channel=channel, status=status_, skip=skip, limit=limit)
    return {"items": [session_out(s) for s in items], "count": len(items)}

@router.get("/channel-sessions/{session_id}", summary="Session detail with full transcript", tags=["Staff Channel Management"])
async def get_session(session_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return session_out(await _svc(db).get_or_404(session_id), include_turns=True)

@router.post("/channel-sessions/{session_id}/message", summary="Add a PAP message turn and get the LLM reply", tags=["Staff Channel Management"])
async def send_message(session_id: uuid.UUID, body: AIChannelMessage, db: DbDep, _: StaffDep) -> dict:
    return await _svc(db).process_message(session_id, body.message)

@router.post("/channel-sessions/{session_id}/submit", summary="Force-submit feedback from current extracted data", tags=["Staff Channel Management"])
async def force_submit(session_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return await _svc(db).force_submit(session_id)

@router.post("/channel-sessions/{session_id}/abandon", summary="Mark session as abandoned", tags=["Staff Channel Management"])
async def abandon_session(session_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    s = await _svc(db).abandon(session_id, body)
    return {"status": s.status.value}


# ═════════════════════════════════════════════════════════════════════════════
# WEBHOOKS — Inbound messages from SMS/WhatsApp gateways
# These are the entry points for fully automated AI conversations.
# When a PAP sends an SMS or WhatsApp message, the gateway forwards it here.
# The system auto-creates a session (if none exists) and runs the LLM pipeline.
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/webhooks/sms", status_code=status.HTTP_200_OK,
             summary="Inbound SMS webhook (Africa's Talking / Twilio)",
             description="Fully automated: PAP sends SMS → AI responds → auto-submits feedback",
             tags=["AI Webhooks"])
async def inbound_sms(request: Request, db: DbDep) -> dict:
    form = await request.form()
    body_dict = dict(form)
    reply = await _svc(db).handle_inbound_sms(body_dict)
    provider = "africas_talking" if "phoneNumber" in body_dict else "twilio"
    return {"message": reply} if provider == "africas_talking" else {"message": "ok", "reply": reply}

@router.post("/webhooks/whatsapp", status_code=status.HTTP_200_OK,
             summary="Inbound WhatsApp webhook (Meta Cloud API)",
             description=(
                 "Fully automated: PAP sends WhatsApp message → AI responds → auto-submits feedback. "
                 "Supports text messages, voice notes (STT → LLM), images, and documents."
             ),
             tags=["AI Webhooks"])
async def inbound_whatsapp(request: Request, db: DbDep) -> dict:
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    try:
        entry    = payload.get("entry", [{}])[0]
        changes  = entry.get("changes", [{}])[0]
        value    = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        msg      = messages[0]
        msg_type = msg.get("type", "text")
        from_num = msg.get("from", "")

        if msg_type == "audio":
            from services.voice_service import VoiceService
            media_id = msg.get("audio", {}).get("id", "")
            if not media_id:
                return {"status": "ok"}

            svc    = VoiceService()
            result = await svc.process_whatsapp_voice_message(
                whatsapp_media_id=media_id,
                from_number=from_num,
            )
            text_payload = {
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "type":      "text",
                                "from":      from_num,
                                "text":      {"body": result.text},
                                "_voice_meta": {
                                    "audio_url":  result.audio_url,
                                    "confidence": result.confidence,
                                    "language":   result.language,
                                    "service":    result.service,
                                    "flagged":    result.flagged_for_review,
                                },
                            }],
                            "contacts": value.get("contacts", []),
                        }
                    }]
                }]
            }
            await _svc(db).handle_inbound_whatsapp(text_payload)
        else:
            await _svc(db).handle_inbound_whatsapp(payload)

    except Exception as exc:
        import structlog
        structlog.get_logger(__name__).error(
            "webhook.whatsapp.handler_error", error=str(exc), exc_info=exc
        )

    return {"status": "ok"}


@router.get("/webhooks/whatsapp", status_code=status.HTTP_200_OK,
            summary="WhatsApp webhook verification (Meta hub.challenge)",
            tags=["AI Webhooks"])
async def verify_whatsapp_webhook(request: Request) -> object:
    from fastapi.responses import PlainTextResponse
    from core.config import settings
    params        = dict(request.query_params)
    mode          = params.get("hub.mode", "")
    token         = params.get("hub.verify_token", "")
    challenge     = params.get("hub.challenge", "")
    verify_token  = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "riviwa_webhook_verify")
    if mode == "subscribe" and token == verify_token:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)
