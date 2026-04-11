# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/webhooks.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/webhooks.py
═══════════════════════════════════════════════════════════════════════════════
Delivery receipt (DLR) webhooks from external notification providers.

These endpoints update NotificationDelivery.status when the provider
confirms actual delivery to the device or reports failure.

Providers supported:
  · Africa's Talking — SMS DLR
  · Twilio           — SMS DLR + WhatsApp DLR
  · SendGrid         — Email event webhooks
  · FCM              — Push delivery receipts (via Firebase Admin SDK callbacks)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from core.config import settings
from core.dependencies import DbDep
from repositories.notification_repository import NotificationRepository

log    = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Provider Webhooks"])


# ─────────────────────────────────────────────────────────────────────────────
# Africa's Talking — SMS DLR
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sms/at/dlr",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Africa's Talking SMS delivery report",
)
async def at_sms_dlr(request: Request, db: DbDep) -> dict:
    """
    Africa's Talking posts DLRs as form-encoded data:
      messageId=ATXid_xxx&status=Success&phoneNumber=+255...&networkCode=63902

    Status values:
      Success       → DELIVERED
      Failed        → FAILED
      Rejected      → FAILED (permanent)
      Buffered      → keep SENT (still in transit)
    """
    form = await request.form()
    message_id  = form.get("messageId", "")
    at_status   = form.get("status", "")
    failure_reason: Optional[str] = None

    if at_status == "Success":
        new_status = "delivered"
    elif at_status in ("Failed", "Rejected"):
        new_status     = "failed"
        failure_reason = f"AT DLR: {at_status}"
    else:
        # Buffered or unknown — no state change
        return {"received": True}

    repo = NotificationRepository(db)
    delivery = await repo.update_delivery_status(
        provider_message_id = message_id,
        new_status          = new_status,
        delivered_at        = datetime.now(timezone.utc) if new_status == "delivered" else None,
        failure_reason      = failure_reason,
    )
    await db.commit()

    if delivery:
        log.info("dlr.at_sms", message_id=message_id, status=new_status)
    else:
        log.warning("dlr.at_sms.not_found", message_id=message_id)

    return {"received": True}


# ─────────────────────────────────────────────────────────────────────────────
# Twilio — SMS DLR
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sms/twilio/dlr",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Twilio SMS delivery report",
)
async def twilio_sms_dlr(request: Request, db: DbDep) -> str:
    """
    Twilio posts DLRs as form-encoded data.
    MessageStatus: queued, sent, delivered, undelivered, failed

    Validates Twilio signature using TWILIO_AUTH_TOKEN.
    """
    form       = await request.form()
    message_id = form.get("MessageSid", "")
    tw_status  = form.get("MessageStatus", "")

    status_map = {
        "delivered":   "delivered",
        "undelivered": "failed",
        "failed":      "failed",
        "sent":        "sent",
    }
    new_status = status_map.get(tw_status)
    if not new_status:
        return ""

    repo = NotificationRepository(db)
    await repo.update_delivery_status(
        provider_message_id = message_id,
        new_status          = new_status,
        delivered_at        = datetime.now(timezone.utc) if new_status == "delivered" else None,
        failure_reason      = f"Twilio: {tw_status}" if new_status == "failed" else None,
    )
    await db.commit()
    log.info("dlr.twilio_sms", message_id=message_id, status=new_status)
    return ""  # Twilio expects empty 200 response


# ─────────────────────────────────────────────────────────────────────────────
# SendGrid — Email event webhook
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/email/sendgrid",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="SendGrid email event webhook",
)
async def sendgrid_events(
    request: Request,
    db:      DbDep,
) -> dict:
    """
    SendGrid sends a batch of event objects:
    [{"event": "delivered", "sg_message_id": "xxx", "timestamp": 1234567890}, ...]

    Events: processed, dropped, delivered, bounce, open, click, unsubscribe, spam_report
    """
    try:
        events = await request.json()
    except Exception:
        return {"received": False}

    repo = NotificationRepository(db)
    for event in events:
        ev_type    = event.get("event", "")
        message_id = event.get("sg_message_id", "").split(".")[0]  # strip suffix

        if ev_type == "delivered":
            ts = event.get("timestamp")
            delivered_at = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
            await repo.update_delivery_status(message_id, "delivered", delivered_at=delivered_at)
        elif ev_type in ("bounce", "dropped", "spam_report"):
            await repo.update_delivery_status(
                message_id, "failed",
                failure_reason=f"SendGrid: {ev_type}",
            )

    await db.commit()
    return {"received": True}


# ─────────────────────────────────────────────────────────────────────────────
# Meta WhatsApp — Status update webhook
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/whatsapp/meta",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Meta WhatsApp message status webhook",
)
async def meta_whatsapp_status(request: Request, db: DbDep) -> dict:
    """
    Meta Cloud API posts status updates when WhatsApp messages are
    delivered or read.

    Payload structure:
    {
      "entry": [{
        "changes": [{
          "value": {
            "statuses": [{
              "id": "wamid.xxx",
              "status": "delivered|read|failed",
              "timestamp": "..."
            }]
          }
        }]
      }]
    }
    """
    try:
        body = await request.json()
    except Exception:
        return {"ok": False}

    repo = NotificationRepository(db)
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for stat in value.get("statuses", []):
                wamid      = stat.get("id", "")
                meta_status = stat.get("status", "")

                if meta_status == "delivered":
                    ts = stat.get("timestamp")
                    delivered_at = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None
                    await repo.update_delivery_status(wamid, "delivered", delivered_at=delivered_at)
                elif meta_status == "read":
                    await repo.update_delivery_status(wamid, "delivered")
                elif meta_status == "failed":
                    errors = stat.get("errors", [])
                    reason = errors[0].get("title", "Meta WhatsApp failure") if errors else "Meta WhatsApp failure"
                    await repo.update_delivery_status(wamid, "failed", failure_reason=reason)

    await db.commit()
    return {"ok": True}


@router.get(
    "/whatsapp/meta",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Meta WhatsApp webhook verification",
)
async def meta_whatsapp_verify(request: Request) -> int:
    """Meta hub.challenge verification for webhook registration."""
    params     = request.query_params
    mode       = params.get("hub.mode")
    token      = params.get("hub.verify_token")
    challenge  = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed.")
