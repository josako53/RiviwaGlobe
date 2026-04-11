"""api/v1/webhooks.py — SMS and WhatsApp inbound webhook handlers."""
from __future__ import annotations
from fastapi import APIRouter, Request, status
from fastapi.responses import PlainTextResponse
from core.config import settings
from core.dependencies import DbDep
from services.conversation_service import ConversationService

router = APIRouter(prefix="/ai", tags=["AI Webhooks"])


def _svc(db) -> ConversationService:
    return ConversationService(db=db)


# ── SMS (Africa's Talking / Twilio) ───────────────────────────────────────────

@router.post(
    "/webhooks/sms",
    status_code=status.HTTP_200_OK,
    summary="Inbound SMS webhook — Africa's Talking / Twilio",
    description=(
        "Fully automated: PAP sends SMS → Rivai AI responds → auto-submits feedback. "
        "Supports Africa's Talking (phoneNumber/text) and Twilio (From/Body) payload formats."
    ),
)
async def inbound_sms(request: Request, db: DbDep) -> dict:
    try:
        form = await request.form()
        body_dict = dict(form)
    except Exception:
        try:
            body_dict = await request.json()
        except Exception:
            return {"message": ""}

    reply = await _svc(db).handle_inbound_sms(body_dict)

    # Africa's Talking expects {"message": reply}
    # Twilio expects TwiML or a plain dict
    provider = "africas_talking" if "phoneNumber" in body_dict else "twilio"
    if provider == "africas_talking":
        return {"message": reply}
    return {"message": "ok", "reply": reply}


# ── WhatsApp (Meta Cloud API) ─────────────────────────────────────────────────

@router.post(
    "/webhooks/whatsapp",
    status_code=status.HTTP_200_OK,
    summary="Inbound WhatsApp webhook — Meta Cloud API",
    description=(
        "Fully automated: PAP sends WhatsApp message → Rivai AI responds → auto-submits feedback. "
        "Supports text messages and voice notes (STT transcription). "
        "Images/documents are accepted as proof attachments."
    ),
)
async def inbound_whatsapp(request: Request, db: DbDep) -> dict:
    import structlog
    log = structlog.get_logger(__name__)
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    try:
        reply = await _svc(db).handle_inbound_whatsapp(payload)
        # Send reply back via WhatsApp API if we have access token and phone number
        if reply and settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
            # Extract sender's WhatsApp ID from payload
            entry    = payload.get("entry", [{}])[0]
            changes  = entry.get("changes", [{}])[0]
            value    = changes.get("value", {})
            messages = value.get("messages", [])
            if messages:
                to_number = messages[0].get("from", "")
                if to_number:
                    await _send_whatsapp_reply(to_number, reply)
    except Exception as exc:
        log.error("ai.webhook.whatsapp.error", error=str(exc), exc_info=exc)

    return {"status": "ok"}


@router.get(
    "/webhooks/whatsapp",
    status_code=status.HTTP_200_OK,
    summary="WhatsApp webhook verification (Meta hub.challenge)",
    tags=["AI Webhooks"],
)
async def verify_whatsapp(request: Request) -> object:
    params   = dict(request.query_params)
    mode     = params.get("hub.mode", "")
    token    = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)


# ── WhatsApp send helper ──────────────────────────────────────────────────────

async def _send_whatsapp_reply(to: str, text: str) -> None:
    """Send a WhatsApp text message back to the PAP via Meta Cloud API."""
    import httpx, structlog
    log = structlog.get_logger(__name__)
    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code not in (200, 201):
                log.warning("ai.whatsapp.send_failed", status=r.status_code, body=r.text[:200])
    except Exception as exc:
        log.error("ai.whatsapp.send_error", error=str(exc))
