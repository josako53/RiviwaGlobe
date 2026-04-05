"""
services/id_verification_provider.py
──────────────────────────────────────────────────────────────────
Provider abstraction for government ID verification.

Pattern: BaseIDVerificationProvider defines the interface.
Each concrete class wraps one provider (Stripe Identity, Onfido, etc.).
get_verification_provider() is the factory — returns the configured
provider based on settings.ID_VERIFICATION_PROVIDER.

Adding a new provider
──────────────────────
  1. Create a class that extends BaseIDVerificationProvider.
  2. Implement create_session() and parse_webhook().
  3. parse_webhook() MUST validate the provider signature before
     returning — raise ValueError on invalid/missing signature.
  4. Register the class in get_verification_provider().

Security invariants
──────────────────────
  · hash_id_number() is a static method — no state, no side effects.
    It must be the only place raw government ID numbers are processed;
    the raw value must never be persisted or logged.
  · Webhook signature validation is mandatory in production.
    Concrete implementations raise NotImplementedError until the
    signature secret is wired up; the StubProvider skips it by design.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import structlog

from core.config import settings
from core.security import hash_sensitive_id
from schemas.fraud import IDVerificationWebhook

log = structlog.get_logger(__name__)

# Default HTTP timeout for all provider API calls (connect + read).
_PROVIDER_TIMEOUT = 10.0   # seconds


# ── Session creation result ────────────────────────────────────────────────────

@dataclass
class VerificationSession:
    """What we get back when we ask the provider to start a session."""
    provider_session_id: str    # stored in IDVerification.provider_session_id
    session_url: str            # URL to redirect the user to
    expires_in_seconds: int = 3600


# ── Base interface ─────────────────────────────────────────────────────────────

class BaseIDVerificationProvider(ABC):

    @abstractmethod
    async def create_session(
        self,
        user_id:   uuid.UUID,
        email:     str,
        full_name: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> VerificationSession:
        """
        Create a verification session with the provider.
        Returns a VerificationSession with the URL to redirect the user to.
        Raises httpx.HTTPError on provider API failure.
        """
        ...

    @abstractmethod
    def parse_webhook(
        self,
        raw_payload: dict,
        signature:   Optional[str] = None,
    ) -> IDVerificationWebhook:
        """
        Parse and validate an incoming webhook payload from the provider.

        Implementations MUST validate the provider signature before
        trusting any payload fields.  Raise ValueError on:
          · missing signature when one is expected
          · signature mismatch
          · malformed payload

        Returns a normalised IDVerificationWebhook on success.
        """
        ...

    @staticmethod
    def hash_id_number(raw_id: str) -> str:
        """
        One-way BLAKE2b-256 hash of the government ID number.

        The raw value is uppercased and whitespace-stripped before hashing
        so that "AB 123 456" and "ab123456" produce the same digest.
        The raw ID number must never be stored, logged, or returned.
        """
        return hash_sensitive_id(raw_id.upper().strip().replace(" ", ""))


# ── Stub (development / CI) ───────────────────────────────────────────────────

class StubIDVerificationProvider(BaseIDVerificationProvider):
    """
    Used in development and tests.

    Returns a session that points to an in-app dev endpoint which
    accepts ?stub_result=approved|rejected and fires a synthetic webhook.
    No real verification takes place.

    Signature validation is intentionally skipped (no secret in dev).
    """

    async def create_session(
        self,
        user_id:   uuid.UUID,
        email:     str,
        full_name: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> VerificationSession:
        session_id = f"stub_session_{uuid.uuid4().hex[:16]}"
        # Use settings.BASE_URL so the URL works in any dev/CI environment,
        # not just localhost:8000.
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000").rstrip("/")
        session_url = (
            f"{base_url}/api/v1/dev/id-verify-stub"
            f"?session_id={session_id}&user_id={user_id}"
        )
        log.info(
            "id_verification.stub.session_created",
            user_id=str(user_id),
            session_id=session_id,
        )
        return VerificationSession(
            provider_session_id=session_id,
            session_url=session_url,
            expires_in_seconds=3600,
        )

    def parse_webhook(
        self,
        raw_payload: dict,
        signature:   Optional[str] = None,
    ) -> IDVerificationWebhook:
        # Stub: payload is already in normalised IDVerificationWebhook format.
        return IDVerificationWebhook(**raw_payload)


# ── Stripe Identity ────────────────────────────────────────────────────────────

class StripeIDVerificationProvider(BaseIDVerificationProvider):
    """
    Stripe Identity: https://stripe.com/docs/identity

    Required settings:
      STRIPE_IDENTITY_API_KEY         — Stripe secret key (sk_live_…)
      ID_VERIFICATION_WEBHOOK_SECRET  — Stripe webhook signing secret (whsec_…)
    """

    async def create_session(
        self,
        user_id:   uuid.UUID,
        email:     str,
        full_name: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> VerificationSession:
        import httpx

        headers = {
            "Authorization": f"Bearer {settings.STRIPE_IDENTITY_API_KEY}",
            "Content-Type":  "application/x-www-form-urlencoded",
        }
        data: dict = {
            "type":              "document",
            "metadata[user_id]": str(user_id),
            "metadata[email]":   email,
        }
        if return_url:
            data["return_url"] = return_url

        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            resp = await client.post(
                "https://api.stripe.com/v1/identity/verification_sessions",
                headers=headers,
                data=data,
            )
            resp.raise_for_status()
            body = resp.json()

        log.info(
            "id_verification.stripe.session_created",
            user_id=str(user_id),
            session_id=body["id"],
        )
        return VerificationSession(
            provider_session_id=body["id"],
            session_url=body["url"],
            expires_in_seconds=3600,
        )

    def parse_webhook(
        self,
        raw_payload: dict,
        signature:   Optional[str] = None,
    ) -> IDVerificationWebhook:
        """
        Validate the Stripe-Signature header and parse the event.

        Stripe HMAC validation:
          https://stripe.com/docs/webhooks/signatures
        """
        webhook_secret = getattr(settings, "ID_VERIFICATION_WEBHOOK_SECRET", None)
        if not webhook_secret:
            raise NotImplementedError(
                "ID_VERIFICATION_WEBHOOK_SECRET must be set in settings before "
                "Stripe webhook validation is active."
            )

        # Stripe signatures look like "t=<timestamp>,v1=<hmac_hex>"
        if not signature:
            raise ValueError("Missing Stripe-Signature header.")

        try:
            sig_parts = {
                item.split("=", 1)[0]: item.split("=", 1)[1]
                for item in signature.split(",")
            }
            timestamp  = sig_parts["t"]
            sig_v1     = sig_parts["v1"]
            raw_body   = raw_payload.get("_raw_body", "")   # caller must attach raw bytes
            signed_payload = f"{timestamp}.{raw_body}"
            expected_sig = hmac.new(
                webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, sig_v1):
                raise ValueError("Stripe webhook signature mismatch.")
        except KeyError as exc:
            raise ValueError(f"Malformed Stripe-Signature header: {exc}") from exc

        event_type = raw_payload.get("type", "")
        obj        = raw_payload.get("data", {}).get("object", {})
        session_id = obj.get("id", "")

        status_map = {
            "identity.verification_session.verified":       "approved",
            "identity.verification_session.requires_input": "rejected",
        }
        status = status_map.get(event_type, "expired")

        verified   = obj.get("verified_outputs", {})
        id_number  = verified.get("id_number")

        return IDVerificationWebhook(
            provider="stripe",
            provider_session_id=session_id,
            status=status,
            id_number_hash=(
                self.hash_id_number(id_number) if id_number else None
            ),
            id_type=verified.get("id_number_type"),
            id_country=verified.get("address", {}).get("country"),
            rejection_reason=obj.get("last_error", {}).get("code"),
            raw_payload=raw_payload,
        )


# ── Onfido ──────────────────────────────────────────────────────────────────────

class OnfidoIDVerificationProvider(BaseIDVerificationProvider):
    """
    Onfido: https://documentation.onfido.com

    Required settings:
      ONFIDO_API_TOKEN               — API token (api_live.…)
      ID_VERIFICATION_WEBHOOK_SECRET — Onfido webhook token for HMAC validation
    """

    async def create_session(
        self,
        user_id:   uuid.UUID,
        email:     str,
        full_name: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> VerificationSession:
        import httpx

        headers = {
            "Authorization": f"Token token={settings.ONFIDO_API_TOKEN}",
            "Content-Type":  "application/json",
        }

        # Parse first / last name from full_name; fall back gracefully.
        parts      = (full_name or "").strip().split(None, 1)
        first_name = parts[0] if parts else "User"
        last_name  = parts[1] if len(parts) > 1 else first_name   # Onfido requires both

        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            # Step 1: create applicant
            r = await client.post(
                "https://api.eu.onfido.com/v3.6/applicants",
                headers=headers,
                json={"first_name": first_name, "last_name": last_name},
            )
            r.raise_for_status()
            applicant_id = r.json()["id"]

            # Step 2: obtain SDK token
            sdk_r = await client.post(
                "https://api.eu.onfido.com/v3.6/sdk_token",
                headers=headers,
                json={"applicant_id": applicant_id, "referrer": "*"},
            )
            sdk_r.raise_for_status()
            sdk_token = sdk_r.json()["token"]

        session_id = f"onfido_{applicant_id}"
        log.info(
            "id_verification.onfido.session_created",
            user_id=str(user_id),
            applicant_id=applicant_id,
        )
        return VerificationSession(
            provider_session_id=session_id,
            session_url=f"https://id.onfido.com/?token={sdk_token}",
            expires_in_seconds=7200,
        )

    def parse_webhook(
        self,
        raw_payload: dict,
        signature:   Optional[str] = None,
    ) -> IDVerificationWebhook:
        """
        Validate Onfido HMAC-SHA256 webhook signature and parse the event.

        Onfido documentation:
          https://documentation.onfido.com/#webhooks
        """
        webhook_token = getattr(settings, "ID_VERIFICATION_WEBHOOK_SECRET", None)
        if not webhook_token:
            raise NotImplementedError(
                "ID_VERIFICATION_WEBHOOK_SECRET must be set in settings before "
                "Onfido webhook validation is active."
            )

        if not signature:
            raise ValueError("Missing X-SHA2-Signature header.")

        raw_body = raw_payload.get("_raw_body", "")
        expected = hmac.new(
            webhook_token.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Onfido webhook signature mismatch.")

        payload      = raw_payload.get("payload", {})
        obj          = payload.get("object", {})
        result       = obj.get("result", "")
        applicant_id = obj.get("applicant_id", "")
        status       = "approved" if result == "clear" else "rejected"

        return IDVerificationWebhook(
            provider="onfido",
            provider_session_id=f"onfido_{applicant_id}",
            status=status,
            rejection_reason=obj.get("sub_result"),
            raw_payload=raw_payload,
        )


# ── Factory ────────────────────────────────────────────────────────────────────

def get_verification_provider() -> BaseIDVerificationProvider:
    """
    Return the configured ID verification provider.
    Defaults to StubIDVerificationProvider when the setting is absent
    or unrecognised — safe for development and CI.
    """
    provider = getattr(settings, "ID_VERIFICATION_PROVIDER", "stub").lower()
    if provider == "stripe":
        return StripeIDVerificationProvider()
    if provider == "onfido":
        return OnfidoIDVerificationProvider()
    if provider != "stub":
        log.warning(
            "id_verification.unknown_provider_falling_back_to_stub",
            configured=provider,
        )
    return StubIDVerificationProvider()
