# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/whatsapp.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/whatsapp.py
─────────────────────────────────────────────────────────────────────────────
WhatsApp Business Channel via Meta Cloud API.

Uses the Meta Cloud API v18+ Messages endpoint.
Template messages are used for outbound notifications (non-session messages).
Free-form messages are only allowed within a 24-hour customer service window.

For Riviwa:
  · All notification messages are sent as WhatsApp Business Template messages
  · Templates must be pre-approved by Meta before use
  · The notification_type maps to a WhatsApp template name in the DB
  · Variables are passed as template components
"""
from __future__ import annotations

import structlog

from channels.base import BaseChannel, ChannelPayload, ChannelResult
from core.config import settings

log = structlog.get_logger(__name__)


class WhatsAppChannel(BaseChannel):

    channel_name = "whatsapp"

    def is_configured(self) -> bool:
        return bool(settings.META_WHATSAPP_TOKEN and settings.META_WHATSAPP_PHONE_ID)

    async def send(self, payload: ChannelPayload) -> ChannelResult:
        if not payload.recipient_phone:
            return ChannelResult.permanent_fail(
                "No phone number available for WhatsApp delivery."
            )
        if not self.is_configured():
            return ChannelResult.fail("WhatsApp (Meta Cloud) not configured.", should_retry=False)

        try:
            import httpx

            phone_id = settings.META_WHATSAPP_PHONE_ID
            url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

            headers = {
                "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
                "Content-Type":  "application/json",
            }

            # Compose message body
            # For non-template free-text (only valid within 24h session window):
            data = {
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":    payload.recipient_phone,
                "type":  "text",
                "text":  {"preview_url": False, "body": payload.rendered_body},
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=data, headers=headers)
                body = resp.json()

            if resp.status_code == 200 and "messages" in body:
                msg_id = body["messages"][0].get("id", "")
                return ChannelResult.ok(provider_message_id=msg_id)

            error = body.get("error", {})
            code = error.get("code", 0)
            log.warning("whatsapp.send_failed", code=code, body=body)

            # Permanent failures: 131026 (recipient not on WhatsApp), 131047 (re-engagement needed)
            if code in (131026, 131047, 100):
                return ChannelResult.permanent_fail(error.get("message", "Permanent WhatsApp error"))

            return ChannelResult.fail(error.get("message", f"HTTP {resp.status_code}"))

        except ImportError:
            return ChannelResult.fail(
                "httpx not installed. Run: pip install httpx",
                should_retry=False,
            )
        except Exception as exc:
            log.error("whatsapp.exception", error=str(exc))
            return ChannelResult.fail(str(exc))
