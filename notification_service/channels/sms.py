# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/sms.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/sms.py
─────────────────────────────────────────────────────────────────────────────
SMS channel — Africa's Talking primary provider, Twilio fallback.

Africa's Talking is the preferred provider for Tanzania and East Africa
due to lower latency, local number support, and delivery report (DLR)
webhooks via /webhooks/sms/at/dlr.

Twilio is used as fallback if AT fails.  Twilio Verify is NOT used here —
that is handled by riviwa_auth_service for OTPs.

Message length:
  · Single SMS:  160 chars (GSM-7) or 70 chars (Unicode/Swahili)
  · Longer messages are automatically split into multi-part SMS by providers
  · Riviwa body templates should stay under 160 chars for single-SMS delivery
"""
from __future__ import annotations

import structlog

from channels.base import BaseChannel, ChannelPayload, ChannelResult
from core.config import settings

log = structlog.get_logger(__name__)


class SMSChannel(BaseChannel):

    channel_name = "sms"

    def is_configured(self) -> bool:
        return bool(settings.AT_API_KEY) or bool(settings.TWILIO_ACCOUNT_SID)

    async def send(self, payload: ChannelPayload) -> ChannelResult:
        if not payload.recipient_phone:
            return ChannelResult.permanent_fail(
                "No phone number available for SMS delivery."
            )

        # ── Try Africa's Talking first ────────────────────────────────────────
        if settings.AT_API_KEY:
            result = await self._send_at(payload)
            if result.success:
                return result
            log.warning("sms.at_failed_trying_twilio",
                        reason=result.failure_reason,
                        phone=payload.recipient_phone[:8] + "****")

        # ── Twilio fallback ───────────────────────────────────────────────────
        if settings.TWILIO_ACCOUNT_SID:
            return await self._send_twilio(payload)

        return ChannelResult.fail("No SMS provider configured.", should_retry=False)

    async def _send_at(self, payload: ChannelPayload) -> ChannelResult:
        """Africa's Talking SMS."""
        try:
            import africastalking as at
            at.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
            sms = at.SMS

            # Africa's Talking SDK is synchronous — run in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: sms.send(
                    message=payload.rendered_body,
                    recipients=[payload.recipient_phone],
                    sender_id=settings.AT_SENDER_ID or None,
                )
            )
            # Response: {"SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "...", ...}]}}
            recipients = response.get("SMSMessageData", {}).get("Recipients", [])
            if recipients:
                rec = recipients[0]
                status_code = rec.get("statusCode", 0)
                if status_code == 101:
                    return ChannelResult.ok(provider_message_id=rec.get("messageId"))
                elif status_code in (401, 402):
                    # Permanently failed (blacklisted, invalid number)
                    return ChannelResult.permanent_fail(rec.get("status", "Permanent failure"))
                else:
                    return ChannelResult.fail(rec.get("status", "Unknown AT error"))
            return ChannelResult.fail("Empty recipient list in AT response")

        except ImportError:
            return ChannelResult.fail(
                "africastalking not installed. Run: pip install africastalking",
                should_retry=False,
            )
        except Exception as exc:
            log.error("sms.at_exception", error=str(exc))
            return ChannelResult.fail(str(exc))

    async def _send_twilio(self, payload: ChannelPayload) -> ChannelResult:
        """Twilio SMS fallback."""
        try:
            from twilio.rest import Client
            import asyncio

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    body=payload.rendered_body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=payload.recipient_phone,
                )
            )
            if message.sid:
                return ChannelResult.ok(provider_message_id=message.sid)
            return ChannelResult.fail("No SID returned by Twilio")

        except ImportError:
            return ChannelResult.fail(
                "twilio not installed. Run: pip install twilio",
                should_retry=False,
            )
        except Exception as exc:
            log.error("sms.twilio_exception", error=str(exc))
            # 21211 = invalid phone number — permanent
            if "21211" in str(exc) or "21614" in str(exc):
                return ChannelResult.permanent_fail(str(exc))
            return ChannelResult.fail(str(exc))
