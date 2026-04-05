# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/email_channel.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/email_channel.py
─────────────────────────────────────────────────────────────────────────────
Email channel — SendGrid primary, SMTP fallback.

The body_template for email channels contains HTML. The rendered_body
is passed as the HTML content. A plain-text version is also derived
by stripping HTML tags.
"""
from __future__ import annotations

import re
import structlog

from channels.base import BaseChannel, ChannelPayload, ChannelResult
from core.config import settings

log = structlog.get_logger(__name__)


def _html_to_plain(html: str) -> str:
    """Very simple HTML → plain text for the text/plain part."""
    return re.sub(r"<[^>]+>", "", html).strip()


class EmailChannel(BaseChannel):

    channel_name = "email"

    def is_configured(self) -> bool:
        return bool(settings.SENDGRID_API_KEY) or bool(settings.SMTP_HOST)

    async def send(self, payload: ChannelPayload) -> ChannelResult:
        if not payload.recipient_email:
            return ChannelResult.permanent_fail(
                "No email address available for email delivery."
            )
        if not self.is_configured():
            return ChannelResult.fail("No email provider configured.", should_retry=False)

        subject = payload.rendered_subject or payload.rendered_title or "Notification from Riviwa"

        # ── Try SendGrid first ────────────────────────────────────────────────
        if settings.SENDGRID_API_KEY:
            result = await self._send_sendgrid(payload, subject)
            if result.success:
                return result
            log.warning("email.sendgrid_failed_trying_smtp", reason=result.failure_reason)

        # ── SMTP fallback ─────────────────────────────────────────────────────
        if settings.SMTP_HOST:
            return await self._send_smtp(payload, subject)

        return ChannelResult.fail("All email providers failed.", should_retry=True)

    async def _send_sendgrid(self, payload: ChannelPayload, subject: str) -> ChannelResult:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Content, To
            import asyncio

            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
            html_content = payload.rendered_body
            plain_content = _html_to_plain(html_content)

            message = Mail(
                from_email=(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
                to_emails=payload.recipient_email,
                subject=subject,
                plain_text_content=plain_content,
                html_content=html_content,
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: sg.send(message))

            if response.status_code in (200, 202):
                msg_id = response.headers.get("X-Message-Id", "")
                return ChannelResult.ok(provider_message_id=msg_id)

            # 4xx permanent
            if 400 <= response.status_code < 500:
                return ChannelResult.permanent_fail(
                    f"SendGrid returned HTTP {response.status_code}"
                )
            return ChannelResult.fail(f"SendGrid returned HTTP {response.status_code}")

        except ImportError:
            return ChannelResult.fail(
                "sendgrid not installed. Run: pip install sendgrid",
                should_retry=False,
            )
        except Exception as exc:
            log.error("email.sendgrid_exception", error=str(exc))
            return ChannelResult.fail(str(exc))

    async def _send_smtp(self, payload: ChannelPayload, subject: str) -> ChannelResult:
        try:
            import asyncio
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg["To"]      = payload.recipient_email

            plain = _html_to_plain(payload.rendered_body)
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(payload.rendered_body, "html", "utf-8"))

            def _send_sync():
                if settings.SMTP_USE_TLS:
                    smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                    smtp.starttls()
                else:
                    smtp = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.sendmail(settings.EMAIL_FROM, [payload.recipient_email], msg.as_string())
                smtp.quit()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send_sync)
            return ChannelResult.ok(provider_message_id="smtp_sent")

        except Exception as exc:
            log.error("email.smtp_exception", error=str(exc))
            return ChannelResult.fail(str(exc))
