"""
api/v1/webhooks.py — Webhook management and delivery history.

Outbound webhooks fire when feedback lifecycle events occur.
The payload is signed with HMAC-SHA256 so partners can verify authenticity.

Partner verifies: HMAC-SHA256(timestamp + "." + body_bytes, signing_secret)
Headers sent:
  X-Riviwa-Signature: sha256=<hex_digest>
  X-Riviwa-Timestamp: <unix_ts>
  X-Riviwa-Event:     feedback.submitted
  X-Riviwa-Delivery:  <delivery_uuid>
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
import sqlalchemy
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from core.security import generate_webhook_signing_secret, sign_webhook_payload
from db.session import get_async_session
from models.integration import (
    IntegrationClient, WebhookDelivery, DeliveryStatus,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/webhooks", tags=["Integration — Webhooks"])


# ── POST /integration/webhooks/test — Send test payload ──────────────────────

@router.post("/test")
async def test_webhook_delivery(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Send a test webhook delivery to the client's configured webhook_url.

    Body:
      event_type  — optional event type to simulate (default: feedback.submitted)
      payload     — optional custom payload dict

    Returns the delivery result including HTTP status code from the partner's endpoint.
    """
    client = ctx.client
    if not client.webhook_url:
        raise HTTPException(
            status_code=400,
            detail={"error": "NO_WEBHOOK_URL",
                    "message": "Configure a webhook_url on the client first"},
        )

    event_type = body.get("event_type", "feedback.submitted")
    test_payload = body.get("payload") or {
        "event":       event_type,
        "test":        True,
        "feedback_id": "00000000-0000-0000-0000-000000000000",
        "client_id":   client.client_id,
        "timestamp":   datetime.utcnow().isoformat(),
    }

    delivery_id = str(uuid.uuid4())
    payload_bytes = __import__("json").dumps(test_payload).encode()

    # We need the raw webhook secret for signing — it's stored as bcrypt hash.
    # For test delivery, generate a temporary secret if none is stored.
    # (In production, the signing secret is stored in a key vault or passed at rotation time)
    # Since webhook_secret_hash is bcrypt, we cannot reverse it — we sign with a test key
    # and advise the partner to use the rotate-webhook-secret endpoint.
    sign_key = f"test_key_{client.client_id}"
    signature, timestamp = sign_webhook_payload(payload_bytes, sign_key)

    headers = {
        "Content-Type":        "application/json",
        "X-Riviwa-Signature":  signature,
        "X-Riviwa-Timestamp":  timestamp,
        "X-Riviwa-Event":      event_type,
        "X-Riviwa-Delivery":   delivery_id,
        "User-Agent":          "Riviwa-Webhook/1.0",
    }

    result = {"success": False, "status_code": None, "error": None}
    try:
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECS) as http:
            resp = await http.post(client.webhook_url, content=payload_bytes, headers=headers)
        result["success"]     = 200 <= resp.status_code < 300
        result["status_code"] = resp.status_code
    except httpx.TimeoutException:
        result["error"] = "TIMEOUT"
    except Exception as exc:
        result["error"] = str(exc)

    log.info("integration.webhook_test",
             client_id=str(client.id), success=result["success"])
    return {
        "delivery_id":  delivery_id,
        "webhook_url":  client.webhook_url,
        "event_type":   event_type,
        "success":      result["success"],
        "status_code":  result["status_code"],
        "error":        result["error"],
        "note":         "Test deliveries use a test signing key. Use rotate-webhook-secret to get a production signing secret.",
    }


# ── POST /integration/webhooks/rotate-secret — Rotate webhook signing secret ─

@router.post("/rotate-secret")
async def rotate_webhook_secret(
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Rotate the webhook signing secret.
    Returns new raw secret (shown ONCE — store securely).
    Partners should update their signature verification logic to use the new secret.
    """
    client = ctx.client
    raw_secret, new_hash = generate_webhook_signing_secret()
    client.webhook_secret_hash = new_hash
    client.updated_at = datetime.utcnow()
    await db.commit()

    log.info("integration.webhook_secret_rotated", client_id=str(client.id))

    return {
        "webhook_signing_secret": raw_secret,
        "warning": "Store this secret securely — it will not be shown again. "
                   "Use HMAC-SHA256(timestamp + '.' + body, secret) to verify deliveries.",
    }


# ── GET /integration/webhooks/deliveries — Delivery history ──────────────────

@router.get("/deliveries")
async def list_deliveries(
    event_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """List webhook delivery history for the authenticated client."""
    q = select(WebhookDelivery).where(
        WebhookDelivery.client_id == ctx.client.id
    )
    if event_type:
        q = q.where(WebhookDelivery.event_type == event_type)
    if status_filter:
        q = q.where(WebhookDelivery.status == status_filter.upper())

    total_q = select(sqlalchemy.func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = (await db.execute(
        q.order_by(WebhookDelivery.created_at.desc())
        .limit(limit).offset(offset)
    )).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_delivery_out(d) for d in rows],
    }


# ── GET /integration/webhooks/deliveries/{id} — Single delivery ──────────────

@router.get("/deliveries/{delivery_id}")
async def get_delivery(
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery or delivery.client_id != ctx.client.id:
        raise HTTPException(404, {"error": "DELIVERY_NOT_FOUND"})
    return _delivery_out(delivery, include_payload=True)


# ── POST /integration/webhooks/deliveries/{id}/retry — Manual retry ──────────

@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Manually trigger a retry for a failed webhook delivery.
    Only allowed when status is FAILED and attempt_count < 10.
    """
    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery or delivery.client_id != ctx.client.id:
        raise HTTPException(404, {"error": "DELIVERY_NOT_FOUND"})
    if delivery.status not in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING):
        raise HTTPException(400, {"error": "CANNOT_RETRY",
                                  "message": f"Delivery status is {delivery.status}"})
    if delivery.attempt_count >= 10:
        raise HTTPException(400, {"error": "MAX_RETRIES_EXCEEDED"})

    delivery.status       = DeliveryStatus.RETRYING
    delivery.next_retry_at = datetime.utcnow()
    await db.commit()

    return {"status": "queued", "delivery_id": str(delivery_id)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _delivery_out(d: WebhookDelivery, include_payload: bool = False) -> dict:
    out = {
        "id":               str(d.id),
        "event_type":       d.event_type,
        "status":           d.status,
        "attempt_count":    d.attempt_count,
        "last_status_code": d.last_status_code,
        "last_error":       d.last_error,
        "next_retry_at":    d.next_retry_at.isoformat()  if d.next_retry_at  else None,
        "delivered_at":     d.delivered_at.isoformat()   if d.delivered_at   else None,
        "failed_at":        d.failed_at.isoformat()      if d.failed_at      else None,
        "created_at":       d.created_at.isoformat(),
    }
    if include_payload:
        out["payload"] = d.payload
    return out
