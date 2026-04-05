"""api/v1/channels.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, Request, status
from core.dependencies import DbDep, StaffDep
from services.channel_service import ChannelService
from api.v1.serialisers import session_out

router = APIRouter(tags=["Channel Sessions"])
def _svc(db): return ChannelService(db=db)

@router.post("/channel-sessions", status_code=status.HTTP_201_CREATED, summary="Start a two-way channel session")
async def create_session(body: Dict[str, Any], db: DbDep, token: StaffDep) -> dict:
    return session_out(await _svc(db).create_session(body, created_by=token.sub))

@router.get("/channel-sessions", summary="List channel sessions")
async def list_sessions(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db).list(project_id=project_id, channel=channel, status=status_, skip=skip, limit=limit)
    return {"items": [session_out(s) for s in items], "count": len(items)}

@router.get("/channel-sessions/{session_id}", summary="Session detail with full transcript")
async def get_session(session_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return session_out(await _svc(db).get_or_404(session_id), include_turns=True)

@router.post("/channel-sessions/{session_id}/message", summary="Add a PAP message turn and get the LLM reply")
async def send_message(session_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    return await _svc(db).process_message(session_id, body["message"])

@router.post("/channel-sessions/{session_id}/submit", summary="Force-submit feedback from current extracted data")
async def force_submit(session_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return await _svc(db).force_submit(session_id)

@router.post("/channel-sessions/{session_id}/abandon", summary="Mark session as abandoned")
async def abandon_session(session_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    s = await _svc(db).abandon(session_id, body)
    return {"status": s.status.value}

@router.post("/webhooks/sms", status_code=status.HTTP_200_OK,
             summary="Inbound SMS webhook (Africa's Talking · Twilio)", include_in_schema=False)
async def inbound_sms(request: Request, db: DbDep) -> dict:
    form = await request.form()
    body_dict = dict(form)
    reply = await _svc(db).handle_inbound_sms(body_dict)
    provider = "africas_talking" if "phoneNumber" in body_dict else "twilio"
    return {"message": reply} if provider == "africas_talking" else {"message": "ok", "reply": reply}

@router.post("/webhooks/whatsapp", status_code=status.HTTP_200_OK,
             summary="Inbound WhatsApp webhook (Meta Cloud API)", include_in_schema=False)
async def inbound_whatsapp(request: Request, db: DbDep) -> dict:
    """
    Handles all inbound WhatsApp messages from Meta Cloud API.

    Meta sends the same webhook URL for both text messages and voice notes.
    This handler inspects the message type and routes accordingly:
      - type = "text"  → normal LLM conversation pipeline
      - type = "audio" → WhatsApp voice note pipeline (STT → LLM)
      - type = "image" / "document" → store as media attachment on active session

    Meta webhook verification (GET request with hub.challenge) is handled
    separately by the GET handler below.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    # Extract message type from Meta's webhook envelope
    try:
        entry    = payload.get("entry", [{}])[0]
        changes  = entry.get("changes", [{}])[0]
        value    = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Delivery status update or other non-message event — acknowledge silently
            return {"status": "ok"}

        msg      = messages[0]
        msg_type = msg.get("type", "text")
        from_num = msg.get("from", "")

        if msg_type == "audio":
            # ── WhatsApp voice note ─────────────────────────────────────────
            # Meta sends OGG/OPUS audio. We transcribe then feed into LLM pipeline.
            from services.voice_service import VoiceService
            media_id = msg.get("audio", {}).get("id", "")
            if not media_id:
                return {"status": "ok"}

            svc    = VoiceService()
            result = await svc.process_whatsapp_voice_message(
                whatsapp_media_id=media_id,
                from_number=from_num,
            )
            # Route the transcript into the normal WhatsApp text pipeline
            # by injecting it as a text message with the same sender number
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
            # ── Text, image, document, location, reaction, etc. ─────────────
            await _svc(db).handle_inbound_whatsapp(payload)

    except Exception as exc:
        import structlog
        structlog.get_logger(__name__).error(
            "webhook.whatsapp.handler_error", error=str(exc), exc_info=exc
        )

    return {"status": "ok"}


@router.get("/webhooks/whatsapp", status_code=status.HTTP_200_OK,
            summary="WhatsApp webhook verification (Meta hub.challenge)", include_in_schema=False)
async def verify_whatsapp_webhook(request: Request) -> object:
    """
    Meta requires a GET endpoint that responds to the hub.challenge verification
    request when you register or update the webhook URL in the Meta developer portal.
    """
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
