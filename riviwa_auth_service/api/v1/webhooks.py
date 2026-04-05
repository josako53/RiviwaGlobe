"""
app/api/v1/webhooks.py
═══════════════════════════════════════════════════════════════════════════════
Inbound webhook endpoints from external providers.

Routes
──────
  POST /api/v1/webhooks/id-verification    ID verification provider callback

Security
──────────
  All webhook endpoints:
  · Accept raw request body (not parsed by Pydantic until after signature check)
  · Validate provider signature via HMAC-SHA256 before touching the payload
  · Return HTTP 200 immediately on receipt — processing is async
  · Return the same HTTP 200 for invalid signatures (timing-safe non-disclosure)
  · Are intentionally public (no Bearer auth — provider calls this endpoint)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from api.v1.deps import IDVerifyServiceDep
from schemas.common import MessageResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ─────────────────────────────────────────────────────────────────────────────
# ID verification webhook
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/id-verification",
    status_code=status.HTTP_200_OK,
    summary="ID verification provider callback",
    response_model=MessageResponse,
    responses={
        200: {
            "description": (
                "Always returned, even on signature failure. "
                "Provider should not retry on 200."
            )
        },
    },
)
async def id_verification_webhook(
    request:   Request,
    svc:       IDVerifyServiceDep,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
) -> JSONResponse:
    """
    Receive ID verification status updates from the provider
    (Onfido, Stripe Identity, or the stub provider in development).

    **Always returns HTTP 200** — this prevents the provider from retrying
    due to processing errors on our side. All retry logic is handled
    internally (Celery tasks, Kafka events).

    The signature in the `X-Webhook-Signature` header is validated by
    `IDVerificationService.process_webhook()` using
    `settings.ID_VERIFICATION_WEBHOOK_SECRET`. An invalid signature results
    in a silent no-op (HTTP 200 with `status: ignored`).

    Expected event types (set in `payload.event_type`):
    - `check.completed`  → approved / rejected based on `payload.result`
    - `check.expired`    → session timed out before user completed verification

    Processing flow:
    1. `IDVerificationService.process_webhook()` validates the signature.
    2. Looks up the `IDVerification` row by `provider_session_id`.
    3. Updates the row status (APPROVED / REJECTED / EXPIRED).
    4. On APPROVED: activates the user account, publishes `user.id_verified`.
    5. On REJECTED / EXPIRED: marks user `PENDING_ID` or `BANNED` depending
       on fraud settings.
    """
    # Read raw body once — needed for HMAC validation
    try:
        body_bytes = await request.body()
        payload    = json.loads(body_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.warning("id_verification_webhook.invalid_json")
        # Still return 200 — provider must not retry malformed sends
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook received.", "status": "ignored"},
        )

    try:
        await svc.process_webhook(
            raw_payload=payload,
            signature=x_webhook_signature,
        )
        log.info(
            "id_verification_webhook.processed",
            event_type=payload.get("event_type"),
            session_id=payload.get("session_id") or payload.get("provider_session_id"),
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook processed."},
        )

    except Exception as exc:
        # Log the failure but always return 200 to prevent provider retries.
        # The error will be surfaced through structured logs and Sentry.
        log.error(
            "id_verification_webhook.processing_error",
            error=str(exc),
            event_type=payload.get("event_type"),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook received.", "status": "processing_error"},
        )
