"""
core/notifications.py
═══════════════════════════════════════════════════════════════════════════════
OTP notification provider abstraction.

Three concrete providers are available:

  TwilioVerifyProvider  — RECOMMENDED for SMS and WhatsApp in production.
                          Twilio generates, sends, and verifies the OTP.
                          You never see the raw code.  Twilio handles:
                            · Cryptographically secure code generation
                            · Delivery and retry logic
                            · 5-attempt lockout (built-in)
                            · 10-minute TTL (built-in)
                          Configure: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
                                     TWILIO_VERIFY_SERVICE_SID

  TwilioSMSProvider     — Uses Twilio Programmable Messaging to deliver a
                          code that YOU generate.  The OTP hash is stored in
                          Redis (existing pattern).  Use when you need custom
                          code length, branding, or a non-Verify workflow.
                          Configure: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
                                     TWILIO_FROM_NUMBER

  EmailOTPProvider      — Sends OTP via SMTP.  The hash is stored in Redis
                          (existing pattern).  Use for email verification flows.
                          Configure: SMTP_HOST, SMTP_PORT, SMTP_USER,
                                     SMTP_PASSWORD, EMAIL_FROM_ADDRESS

  StubOTPProvider       — Development / CI.  Logs the code (when DEBUG=True),
                          stores hash in Redis.  No external calls.

Provider selection
──────────────────
  OTP_SMS_PROVIDER   = "twilio_verify" | "twilio_sms" | "stub"  (default stub)
  OTP_EMAIL_PROVIDER = "smtp" | "stub"                          (default stub)

Factory function
────────────────
  get_sms_provider()    → BaseOTPProvider for SMS/WhatsApp flows
  get_email_provider()  → BaseOTPProvider for email flows

Redis session payload per provider
────────────────────────────────────
  twilio_verify:  { "provider": "twilio_verify", "to": "+254..." }
  twilio_sms:     { "provider": "twilio_sms",    "otp_hash": "...", "to": "+254..." }
  smtp:           { "provider": "smtp",           "otp_hash": "...", "to": "alice@..." }
  stub:           { "provider": "stub",           "otp_hash": "..." }

Security notes
──────────────
  · TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_VERIFY_SERVICE_SID
    must be set as environment variables.  Never hardcode credentials.
  · Rotate credentials immediately if accidentally exposed.
  · For Twilio Verify, you never store or see the raw OTP code.
    Twilio holds it for up to 10 minutes before expiry.
  · For local OTP generation (twilio_sms / smtp / stub), only sha256(code)
    is stored — the raw code is sent to the user and never persisted.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx
import structlog

from core.config import settings
from core.security import generate_otp, hash_otp

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base interface
# ─────────────────────────────────────────────────────────────────────────────

class BaseOTPProvider(ABC):
    """
    Abstract OTP delivery provider.

    Two methods:
      send_otp()   — dispatch a verification code to the recipient.
                     Returns a session_payload dict to be stored in Redis.
      verify_otp() — verify a code submitted by the user.
                     Takes the Redis session_payload and the user-submitted code.
                     Returns True on success.

    The session_payload returned by send_otp() is stored in the Redis key
    (e.g. login:<token>) alongside any other session fields (user_id, etc.).
    It is passed back verbatim to verify_otp() — providers must treat it as
    opaque from the service layer's perspective.
    """

    @abstractmethod
    async def send_otp(
        self,
        to:          str,
        channel:     str = "sms",   # "sms" | "email" | "whatsapp"
        display_name: Optional[str] = None,
        purpose:     str = "verification",
    ) -> dict:
        """
        Send a one-time code to `to`.

        Args:
            to:           E.164 phone number (+254760696054) or email address.
            channel:      Delivery channel.  Twilio Verify supports "sms",
                          "whatsapp", "email", "call".
            display_name: Optional recipient name for personalised messages.
            purpose:      Human-readable context for the message body
                          e.g. "login", "registration", "password reset".

        Returns:
            dict  — session_payload to store in Redis alongside user_id.
                    Shape is provider-specific (see module docstring).
        """
        ...

    @abstractmethod
    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        """
        Verify a code submitted by the user.

        Args:
            submitted_code:  The 6-digit code entered by the user.
            session_payload: The dict returned by send_otp() and stored in Redis.

        Returns:
            True   — code is correct / approved.
            False  — code is wrong; caller should increment attempt counter.

        Raises:
            OTPExpiredError   — Twilio says the session has expired.
            OTPMaxAttemptsError — Twilio says too many wrong attempts.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Twilio Verify  (RECOMMENDED for production SMS)
# ─────────────────────────────────────────────────────────────────────────────

class TwilioVerifyProvider(BaseOTPProvider):
    """
    OTP via Twilio Verify API.

    Twilio generates, sends, and verifies the code.  We never store the
    raw OTP.  The Verify service handles TTL, attempt limiting, and retries.

    Required settings (environment variables):
        TWILIO_ACCOUNT_SID        — starts with AC...
        TWILIO_AUTH_TOKEN         — 32-char hex string
        TWILIO_VERIFY_SERVICE_SID — starts with VA...

    Verify supports channels: sms, whatsapp, call, email
    (email requires configuring a Verify email template in the Twilio console).
    """

    def __init__(self) -> None:
        try:
            from twilio.rest import Client as TwilioClient
        except ImportError:
            raise ImportError(
                "twilio is required for TwilioVerifyProvider. "
                "Add 'twilio>=8.0' to requirements.txt."
            )
        self._client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self._service_sid = settings.TWILIO_VERIFY_SERVICE_SID

    async def send_otp(
        self,
        to:          str,
        channel:     str = "sms",
        display_name: Optional[str] = None,
        purpose:     str = "verification",
    ) -> dict:
        """
        Call Twilio Verify to generate and send the OTP.

        Twilio blocks the request until the SMS is dispatched
        (typically < 1 s).  We run it in a thread pool executor to avoid
        blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        verification = await loop.run_in_executor(
            None,
            lambda: (
                self._client.verify
                .v2
                .services(self._service_sid)
                .verifications
                .create(to=to, channel=channel)
            ),
        )

        log.info(
            "otp.twilio_verify.sent",
            to=_mask_recipient(to),
            channel=channel,
            purpose=purpose,
            verification_sid=verification.sid,
        )

        # We only store metadata — no hash because Twilio holds the code.
        return {
            "provider":          "twilio_verify",
            "to":                to,
            "channel":           channel,
            "verification_sid":  verification.sid,
        }

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        """
        Ask Twilio whether the submitted code is correct.

        Twilio returns status "approved" or "pending".
        "pending" means the code is wrong; Twilio increments its own
        attempt counter and will return an error after 5 wrong attempts.
        """
        from core.exceptions import OTPExpiredError, OTPMaxAttemptsError

        to = session_payload["to"]

        loop = asyncio.get_event_loop()
        try:
            check = await loop.run_in_executor(
                None,
                lambda: (
                    self._client.verify
                    .v2
                    .services(self._service_sid)
                    .verification_checks
                    .create(to=to, code=submitted_code)
                ),
            )
        except Exception as exc:
            # Twilio raises TwilioRestException on expired / max-attempts
            exc_str = str(exc).lower()
            if "60202" in str(exc) or "max attempts" in exc_str:
                raise OTPMaxAttemptsError() from exc
            if "60203" in str(exc) or "expired" in exc_str or "not found" in exc_str:
                raise OTPExpiredError() from exc
            # Unknown error — log and treat as wrong code
            log.error(
                "otp.twilio_verify.check_error",
                to=_mask_recipient(to),
                error=str(exc),
            )
            return False

        approved = check.status == "approved"

        log.info(
            "otp.twilio_verify.checked",
            to=_mask_recipient(to),
            status=check.status,
            approved=approved,
        )
        return approved


# ─────────────────────────────────────────────────────────────────────────────
# Twilio SMS (Programmable Messaging)  — our own OTP, Twilio delivers it
# ─────────────────────────────────────────────────────────────────────────────

class TwilioSMSProvider(BaseOTPProvider):
    """
    OTP via Twilio Programmable Messaging.

    WE generate the 6-digit code, hash it, and store the hash in Redis.
    Twilio only delivers the SMS.  Use this when:
      · You need a custom code format or length.
      · You want full control over the message body (custom branding).
      · You prefer not to use Twilio Verify for policy reasons.

    Required settings:
        TWILIO_ACCOUNT_SID  — starts with AC...
        TWILIO_AUTH_TOKEN   — 32-char hex string
        TWILIO_FROM_NUMBER  — E.164 number you own in Twilio (+1234567890)
                             OR a Messaging Service SID (MG...)
    """

    def __init__(self) -> None:
        try:
            from twilio.rest import Client as TwilioClient
        except ImportError:
            raise ImportError(
                "twilio is required for TwilioSMSProvider. "
                "Add 'twilio>=8.0' to requirements.txt."
            )
        self._client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self._from = settings.TWILIO_FROM_NUMBER

    async def send_otp(
        self,
        to:           str,
        channel:      str = "sms",
        display_name: Optional[str] = None,
        purpose:      str = "verification",
    ) -> dict:
        otp_code = generate_otp()
        otp_hash = hash_otp(otp_code)

        body = _build_sms_body(otp_code, purpose)

        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                to=to,
                from_=self._from,
                body=body,
            ),
        )

        log.info(
            "otp.twilio_sms.sent",
            to=_mask_recipient(to),
            message_sid=message.sid,
            purpose=purpose,
            code="[redacted]" if not getattr(settings, "DEBUG", False) else otp_code,
        )

        # Store hash — we verify locally in verify_otp()
        return {
            "provider":    "twilio_sms",
            "to":          to,
            "otp_hash":    otp_hash,
            "message_sid": message.sid,
        }

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        """
        Local constant-time comparison against the stored SHA-256 hash.
        Attempt counting and TTL management are handled by the service layer.
        """
        import hmac
        import hashlib

        stored_hash    = session_payload.get("otp_hash", "")
        submitted_hash = hashlib.sha256(submitted_code.encode()).hexdigest()
        return hmac.compare_digest(submitted_hash, stored_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Email OTP (SMTP)
# ─────────────────────────────────────────────────────────────────────────────

class EmailOTPProvider(BaseOTPProvider):
    """
    OTP via SMTP email.

    WE generate and hash the OTP.  Delivery is via standard SMTP.

    Required settings:
        SMTP_HOST          — e.g. "smtp.gmail.com", "smtp.sendgrid.net"
        SMTP_PORT          — 587 (STARTTLS) or 465 (SSL)
        SMTP_USER          — SMTP username / API key username
        SMTP_PASSWORD      — SMTP password / API key
        EMAIL_FROM_ADDRESS — "Riviwa <noreply@riviwa.com>"
        SMTP_USE_TLS       — True (default) for STARTTLS on port 587

    For Gmail use an App Password (not your account password).
    For SendGrid set SMTP_USER="apikey" and SMTP_PASSWORD=<sendgrid_api_key>.
    """

    async def send_otp(
        self,
        to:           str,
        channel:      str = "email",
        display_name: Optional[str] = None,
        purpose:      str = "verification",
    ) -> dict:
        otp_code = generate_otp()
        otp_hash = hash_otp(otp_code)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _send_smtp(to, otp_code, display_name, purpose),
        )

        log.info(
            "otp.email.sent",
            to=_mask_recipient(to),
            purpose=purpose,
        )

        return {
            "provider":  "smtp",
            "to":        to,
            "otp_hash":  otp_hash,
        }

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        import hmac
        import hashlib

        stored_hash    = session_payload.get("otp_hash", "")
        submitted_hash = hashlib.sha256(submitted_code.encode()).hexdigest()
        return hmac.compare_digest(submitted_hash, stored_hash)


def _send_smtp(
    to_email:     str,
    otp_code:     str,
    display_name: Optional[str],
    purpose:      str,
) -> None:
    """
    Blocking SMTP send — call via run_in_executor() to avoid blocking asyncio.
    """
    name = display_name or "there"
    subject, html_body, text_body = _build_email_body(otp_code, name, purpose)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = getattr(settings, "EMAIL_FROM_ADDRESS", "noreply@riviwa.com")
    msg["To"]      = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    smtp_host     = getattr(settings, "SMTP_HOST", "localhost")
    smtp_port     = int(getattr(settings, "SMTP_PORT", 587))
    smtp_user     = getattr(settings, "SMTP_USER", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")

    context = ssl.create_default_context()

    # Port 465 = implicit SSL (SMTP_SSL).  Port 587/25 = STARTTLS.
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.sendmail(msg["From"], to_email, msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.sendmail(msg["From"], to_email, msg.as_string())


# ─────────────────────────────────────────────────────────────────────────────
# Stub provider  (development / CI)
# ─────────────────────────────────────────────────────────────────────────────

class StubOTPProvider(BaseOTPProvider):
    """
    No external calls — for development and automated tests.

    · Logs the raw OTP code when DEBUG=True.
    · Stores the hash in the session payload (same as TwilioSMSProvider).
    · Verifies locally via hmac.compare_digest.
    """

    async def send_otp(
        self,
        to:           str,
        channel:      str = "sms",
        display_name: Optional[str] = None,
        purpose:      str = "verification",
    ) -> dict:
        otp_code = generate_otp()
        otp_hash = hash_otp(otp_code)

        log.info(
            "otp.stub.sent",
            to=_mask_recipient(to),
            channel=channel,
            purpose=purpose,
            code=otp_code if getattr(settings, "DEBUG", False) else "[hidden — set DEBUG=True to see]",
        )

        return {
            "provider": "stub",
            "to":       to,
            "otp_hash": otp_hash,
        }

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        import hmac
        import hashlib

        stored_hash    = session_payload.get("otp_hash", "")
        submitted_hash = hashlib.sha256(submitted_code.encode()).hexdigest()
        return hmac.compare_digest(submitted_hash, stored_hash)



# ─────────────────────────────────────────────────────────────────────────────
# Dev bypass provider  (ENVIRONMENT=development only)
# ─────────────────────────────────────────────────────────────────────────────

class DevOTPProvider(BaseOTPProvider):
    """
    Zero-friction OTP provider for local development.

    · send_otp() — never calls any external service.
                   Always logs the fixed code 000000.
                   Returns a session payload so the flow works end-to-end.

    · verify_otp() — accepts ONLY "000000" as a valid code.
                     Any other code returns False (still exercises the
                     attempt-counter logic in the service layer).

    Activated automatically when ENVIRONMENT=development OR ENVIRONMENT=staging,
    regardless of OTP_SMS_PROVIDER / OTP_EMAIL_PROVIDER settings.

    Use staging on a shared/public server (e.g. Contabo demo) while Twilio
    is not yet configured — gives a predictable code without real SMS delivery.

    NEVER enable in production. The factory functions guard this with an
    explicit ENVIRONMENT check.
    """

    _DEV_CODE = "000000"

    async def send_otp(
        self,
        to:           str,
        channel:      str = "sms",
        display_name: Optional[str] = None,
        purpose:      str = "verification",
    ) -> dict:
        log.info(
            "otp.dev.sent",
            to=_mask_recipient(to),
            channel=channel,
            purpose=purpose,
            code=self._DEV_CODE,           # always visible in dev logs
            note="DEV MODE — use 000000 to verify. No SMS/email sent.",
        )
        return {
            "provider": "dev",
            "to":       to,
            "dev_mode": True,
        }

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        import hmac
        # Constant-time comparison even in dev — avoids timing side-channels
        # in case this accidentally runs in a staging environment.
        result = hmac.compare_digest(submitted_code.strip(), self._DEV_CODE)
        log.info(
            "otp.dev.verified",
            submitted=submitted_code,
            accepted=result,
            note="DEV MODE — only 000000 is accepted.",
        )
        return result

# ─────────────────────────────────────────────────────────────────────────────
# Karibu OTP API  (Briq Tanzania)  — RECOMMENDED for Tanzania deployments
# ─────────────────────────────────────────────────────────────────────────────

class KaribuOTPProvider(BaseOTPProvider):
    """
    OTP via the Karibu OTP API (https://karibu.briq.tz).

    Karibu generates, delivers, and verifies codes — we never see the plaintext.
    The code is bcrypt-hashed on Karibu's side; only the recipient sees it via
    SMS, voice call, or WhatsApp.

    Channels supported:
        "sms"       → SMS (default; sender_id and message_template customisable)
        "call"      → TTS voice call
        "whatsapp"  → platform-managed briq_otp Meta template (sender auto-resolved)

    Phone format:
        Karibu requires E.164 digits-only (no +).
        Riviwa stores numbers with a leading +.  _normalise_phone() strips it.

    Session payload stored in Redis:
        { "provider": "karibu", "to": "255712345678", "channel": "sms" }
        No hash is stored — Karibu holds the code internally.

    Error mapping:
        "Max verification attempts reached"  →  OTPMaxAttemptsError
        "No valid OTP found"                 →  OTPExpiredError
        HTTP 401 / 403                       →  Exception (operator config error)
        WhatsApp 400 (template/sender error) →  Exception (caller should retry on sms)

    Required config (env vars):
        KARIBU_API_KEY   —  X-API-Key header value (your developer API key)
        KARIBU_APP_KEY   —  app_key body field (your Developer App key)

    Optional config:
        KARIBU_BASE_URL      —  default https://karibu.briq.tz
        KARIBU_SENDER_ID     —  SMS sender ID shown to recipient (blank = platform default)
        KARIBU_OTP_TTL_MIN   —  OTP lifetime in minutes (default 10)
    """

    def __init__(self) -> None:
        self._api_key  = settings.KARIBU_API_KEY
        self._app_key  = settings.KARIBU_APP_KEY
        self._base_url = getattr(settings, "KARIBU_BASE_URL", "https://karibu.briq.tz").rstrip("/")
        self._sender   = getattr(settings, "KARIBU_SENDER_ID", "")
        self._otp_len  = getattr(settings, "OTP_LENGTH", 6)
        self._ttl_min  = getattr(settings, "KARIBU_OTP_TTL_MIN", 10)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalise_phone(phone: str) -> str:
        """Strip leading + — Karibu requires E.164 digits only (no +)."""
        return phone.lstrip("+")

    def _build_sms_template(self, purpose: str) -> str:
        label = {
            "login":          "login",
            "registration":   "registration",
            "password_reset": "password reset",
            "phone_verify":   "phone verification",
        }.get(purpose, "verification")
        return (
            f"Your Riviwa {label} OTP is: {{otp}}. "
            f"Expires in {{expiry}} minutes. Never share it."
        )

    async def _post(self, path: str, payload: dict) -> dict:
        """Async POST to Karibu API. Returns parsed JSON body."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        # 401/403 come back as {"detail": "..."} — not the envelope
        if resp.status_code in (401, 403):
            raise Exception(
                f"Karibu OTP auth error {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

    # ── BaseOTPProvider interface ─────────────────────────────────────────────

    async def send_otp(
        self,
        to:           str,
        channel:      str = "sms",
        display_name: Optional[str] = None,
        purpose:      str = "verification",
    ) -> dict:
        phone  = self._normalise_phone(to)
        k_ch   = channel if channel in ("sms", "call", "whatsapp") else "sms"

        payload: dict = {
            "phone_number":      phone,
            "app_key":           self._app_key,
            "delivery_method":   k_ch,
            "otp_length":        self._otp_len,
            "minutes_to_expire": self._ttl_min,
        }
        # SMS-only optional fields — ignored on call/whatsapp
        if k_ch == "sms":
            if self._sender:
                payload["sender_id"] = self._sender
            payload["message"] = self._build_sms_template(purpose)

        body = await self._post("/v1/otp/request", payload)

        if not body.get("success"):
            log.error(
                "otp.karibu.send_failed",
                to=_mask_recipient(to),
                channel=k_ch,
                message=body.get("message", "unknown"),
            )
            raise Exception(f"Karibu OTP send failed: {body.get('message')}")

        log.info(
            "otp.karibu.sent",
            to=_mask_recipient(to),
            channel=k_ch,
            purpose=purpose,
            expires_at=(body.get("data") or {}).get("expires_at"),
        )
        # No hash stored — Karibu holds the code internally (bcrypt)
        return {"provider": "karibu", "to": phone, "channel": k_ch}

    async def verify_otp(
        self,
        submitted_code:  str,
        session_payload: dict,
    ) -> bool:
        from core.exceptions import OTPExpiredError, OTPMaxAttemptsError

        phone = session_payload["to"]   # digits-only, set by send_otp()

        body = await self._post("/v1/otp/verify", {
            "phone_number": phone,
            "app_key":      self._app_key,
            "code":         submitted_code,
        })

        if body.get("success"):
            log.info("otp.karibu.verified", to=_mask_recipient(phone))
            return True

        msg       = (body.get("message") or "").lower()
        remaining = (body.get("data") or {}).get("remaining_attempts", 0)

        log.info(
            "otp.karibu.verify_failed",
            to=_mask_recipient(phone),
            message=body.get("message"),
            remaining_attempts=remaining,
        )

        if "max verification attempts" in msg or remaining == 0:
            raise OTPMaxAttemptsError()
        if "no valid otp" in msg:
            raise OTPExpiredError()

        # Wrong code — caller increments attempt counter
        return False

    # ── Extra lifecycle methods (Karibu-specific) ─────────────────────────────

    async def resend_otp(
        self,
        to:      str,
        channel: str = "sms",
        purpose: str = "verification",
    ) -> dict:
        """
        Resend path — uses Karibu's /resend endpoint (same as /request but
        logged separately on Karibu's side for analytics).
        Invalidates the prior active OTP before issuing the new one.
        """
        phone  = self._normalise_phone(to)
        k_ch   = channel if channel in ("sms", "call", "whatsapp") else "sms"

        payload: dict = {
            "phone_number":      phone,
            "app_key":           self._app_key,
            "delivery_method":   k_ch,
            "otp_length":        self._otp_len,
            "minutes_to_expire": self._ttl_min,
        }
        if k_ch == "sms":
            if self._sender:
                payload["sender_id"] = self._sender
            payload["message"] = self._build_sms_template(purpose)

        body = await self._post("/v1/otp/resend", payload)

        if not body.get("success"):
            log.error(
                "otp.karibu.resend_failed",
                to=_mask_recipient(to),
                message=body.get("message"),
            )
            raise Exception(f"Karibu OTP resend failed: {body.get('message')}")

        log.info("otp.karibu.resent", to=_mask_recipient(to), channel=k_ch)
        return {"provider": "karibu", "to": phone, "channel": k_ch}

    async def invalidate_otp(self, to: str) -> None:
        """
        Force-expire the active OTP for this phone.
        Call on logout, phone number change, or any security event.
        Idempotent — safe when no active OTP exists.
        """
        phone = self._normalise_phone(to)
        await self._post("/v1/otp/invalidate", {
            "phone_number": phone,
            "app_key":      self._app_key,
        })
        log.info("otp.karibu.invalidated", to=_mask_recipient(to))

    async def get_otp_status(self, to: str) -> dict:
        """
        Inspect the active OTP for a phone without triggering a send.
        Returns Karibu's data payload: {is_valid, expires_at, remaining_attempts}
        or an empty dict when no active OTP exists.
        Useful for driving countdown timers and idempotent resend UX.
        """
        phone = self._normalise_phone(to)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}/v1/otp/status",
                headers={"X-API-Key": self._api_key},
                params={"phone_number": phone, "app_key": self._app_key},
            )
        body = resp.json()
        # 200 OK even when no active OTP (envelope status_code 404)
        if body.get("success"):
            return body.get("data") or {}
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Factory functions
# ─────────────────────────────────────────────────────────────────────────────

def get_sms_provider() -> BaseOTPProvider:
    """
    Return the configured SMS OTP provider.

    Reads settings.OTP_SMS_PROVIDER:
      "twilio_verify" → TwilioVerifyProvider  (RECOMMENDED for production)
      "twilio_sms"    → TwilioSMSProvider
      "stub"          → StubOTPProvider       (default — safe for dev/CI)

    When ENVIRONMENT=development, DevOTPProvider is returned automatically
    regardless of OTP_SMS_PROVIDER — no external calls, code is always 000000.
    """
    env = getattr(settings, "ENVIRONMENT", "production").lower()
    if env in ("development", "staging"):
        log.info(
            "notifications.dev_otp_provider_active",
            environment=env,
            note="OTP is always 000000 — not for production use.",
        )
        return DevOTPProvider()

    provider = getattr(settings, "OTP_SMS_PROVIDER", "stub").lower()

    if provider == "karibu":
        return KaribuOTPProvider()

    if provider == "twilio_verify":
        return TwilioVerifyProvider()

    if provider == "twilio_sms":
        return TwilioSMSProvider()

    if provider != "stub":
        log.warning(
            "notifications.unknown_sms_provider_falling_back_to_stub",
            configured=provider,
        )
    return StubOTPProvider()


def get_email_provider() -> BaseOTPProvider:
    """
    Return the configured email OTP provider.

    Reads settings.OTP_EMAIL_PROVIDER:
      "smtp" → EmailOTPProvider
      "stub" → StubOTPProvider  (default)

    When ENVIRONMENT=development, DevOTPProvider is returned automatically
    regardless of OTP_EMAIL_PROVIDER — no external calls, code is always 000000.
    """
    env = getattr(settings, "ENVIRONMENT", "production").lower()
    if env in ("development", "staging"):
        log.info(
            "notifications.dev_otp_provider_active",
            environment=env,
            note="OTP is always 000000 — not for production use.",
        )
        return DevOTPProvider()

    provider = getattr(settings, "OTP_EMAIL_PROVIDER", "stub").lower()

    if provider == "smtp":
        return EmailOTPProvider()

    if provider != "stub":
        log.warning(
            "notifications.unknown_email_provider_falling_back_to_stub",
            configured=provider,
        )
    return StubOTPProvider()


def get_provider_for_channel(channel: str) -> BaseOTPProvider:
    """
    Convenience: return the right provider based on the delivery channel.

    "sms" | "whatsapp" → get_sms_provider()
    "email"            → get_email_provider()
    """
    if channel in ("sms", "whatsapp", "call"):
        return get_sms_provider()
    if channel == "email":
        return get_email_provider()
    log.warning("notifications.unknown_channel", channel=channel)
    return StubOTPProvider()


# ─────────────────────────────────────────────────────────────────────────────
# Message body helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_sms_body(otp_code: str, purpose: str) -> str:
    """Build the SMS message body for a given purpose."""
    purpose_text = {
        "login":          "Your Riviwa login code",
        "registration":   "Your Riviwa registration code",
        "password_reset": "Your Riviwa password reset code",
        "phone_verify":   "Your Riviwa phone verification code",
        "email_verify":   "Your Riviwa email verification code",
    }.get(purpose, "Your Riviwa verification code")

    return (
        f"{purpose_text} is: {otp_code}\n"
        f"This code expires in 10 minutes. "
        f"Never share it with anyone."
    )


def _build_email_body(
    otp_code:     str,
    display_name: str,
    purpose:      str,
) -> tuple[str, str, str]:
    """
    Returns (subject, html_body, plain_text_body).
    Replace the HTML with your own branded template.
    """
    purpose_label = {
        "login":          "Sign in",
        "registration":   "Registration",
        "password_reset": "Password Reset",
        "phone_verify":   "Phone Verification",
        "email_verify":   "Email Verification",
    }.get(purpose, "Verification")

    subject = f"Riviwa {purpose_label} Code: {otp_code}"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #1a1a1a;">Riviwa {purpose_label}</h2>
  <p>Hi {display_name},</p>
  <p>Your verification code is:</p>
  <div style="background: #f4f4f4; border-radius: 8px; padding: 20px;
              text-align: center; font-size: 36px; font-weight: bold;
              letter-spacing: 12px; color: #1a1a1a;">
    {otp_code}
  </div>
  <p style="color: #666; font-size: 14px; margin-top: 16px;">
    This code expires in <strong>10 minutes</strong>.
    Never share it with anyone — Riviwa staff will never ask for it.
  </p>
  <p style="color: #999; font-size: 12px;">
    If you did not request this code, please ignore this email.
  </p>
</body>
</html>
"""

    text_body = (
        f"Riviwa {purpose_label}\n\n"
        f"Hi {display_name},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in 10 minutes.\n"
        f"Never share it with anyone.\n\n"
        f"If you did not request this, ignore this email."
    )

    return subject, html_body, text_body


def _mask_recipient(recipient: str) -> str:
    """Privacy-safe masking for logs."""
    if "@" in recipient:
        local, _, domain = recipient.partition("@")
        return f"{local[:2]}***@{domain}"
    if recipient.startswith("+"):
        return recipient[:4] + "***" + recipient[-4:]
    return recipient[:3] + "***"
