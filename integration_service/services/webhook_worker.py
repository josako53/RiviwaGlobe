"""
services/webhook_worker.py — Outbound webhook delivery engine.

Responsibilities:
  - Deliver webhook payloads to partner endpoints
  - Sign payloads with HMAC-SHA256
  - Exponential backoff retry: 30s → 5m → 30m (3 attempts)
  - Update delivery status in DB on success/failure
  - APScheduler polls every 15s for pending/retrying deliveries

Usage:
  Called from main.py lifespan via APScheduler.
  Also callable directly: await deliver_webhook(db, delivery_id)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import sign_webhook_payload
from db.session import AsyncSessionLocal
from models.integration import DeliveryStatus, IntegrationClient, WebhookDelivery

log = structlog.get_logger(__name__)

_RETRY_DELAYS = settings.WEBHOOK_RETRY_DELAYS   # [30, 300, 1800] seconds


async def deliver_webhook(db: AsyncSession, delivery: WebhookDelivery) -> bool:
    """
    Attempt a single webhook delivery.
    Returns True on HTTP 2xx, False otherwise.
    Updates delivery record in-place (caller must commit).
    """
    client = await db.get(IntegrationClient, delivery.client_id)
    if not client or not client.webhook_url:
        delivery.status   = DeliveryStatus.FAILED
        delivery.last_error = "NO_WEBHOOK_URL"
        delivery.failed_at  = datetime.utcnow()
        return False

    payload_bytes = json.dumps(delivery.payload).encode()

    # Sign with stored secret hash — we use the hash as the HMAC key directly.
    # Partners rotate secrets via POST /integration/webhooks/rotate-secret which
    # gives them the raw secret to verify with.
    sign_key = client.webhook_secret_hash or client.client_id
    signature, timestamp = sign_webhook_payload(payload_bytes, sign_key)

    headers = {
        "Content-Type":       "application/json",
        "X-Riviwa-Signature": signature,
        "X-Riviwa-Timestamp": timestamp,
        "X-Riviwa-Event":     delivery.event_type,
        "X-Riviwa-Delivery":  str(delivery.id),
        "User-Agent":         "Riviwa-Webhook/1.0",
    }

    delivery.attempt_count += 1
    try:
        async with httpx.AsyncClient(
            timeout=settings.WEBHOOK_TIMEOUT_SECS,
            follow_redirects=True,
        ) as http:
            resp = await http.post(
                client.webhook_url, content=payload_bytes, headers=headers
            )

        delivery.last_status_code = resp.status_code

        if 200 <= resp.status_code < 300:
            delivery.status       = DeliveryStatus.DELIVERED
            delivery.delivered_at = datetime.utcnow()
            delivery.next_retry_at = None
            log.info("webhook.delivered",
                     delivery_id=str(delivery.id),
                     client_id=str(client.id),
                     event=delivery.event_type,
                     status_code=resp.status_code)
            return True

        # Non-2xx — schedule retry or fail
        delivery.last_error = f"HTTP_{resp.status_code}"

    except httpx.TimeoutException:
        delivery.last_error = "TIMEOUT"
    except Exception as exc:
        delivery.last_error = str(exc)[:500]

    # Schedule retry or mark final failure
    if delivery.attempt_count < settings.WEBHOOK_MAX_RETRIES:
        delay = _RETRY_DELAYS[delivery.attempt_count - 1] if \
                delivery.attempt_count - 1 < len(_RETRY_DELAYS) else _RETRY_DELAYS[-1]
        delivery.status        = DeliveryStatus.RETRYING
        delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        log.warning("webhook.retry_scheduled",
                    delivery_id=str(delivery.id),
                    attempt=delivery.attempt_count,
                    next_retry_in_secs=delay)
    else:
        delivery.status    = DeliveryStatus.FAILED
        delivery.failed_at = datetime.utcnow()
        delivery.next_retry_at = None
        log.error("webhook.delivery_failed_permanently",
                  delivery_id=str(delivery.id),
                  client_id=str(client.id),
                  event=delivery.event_type,
                  attempts=delivery.attempt_count)

    return False


async def process_pending_deliveries() -> None:
    """
    APScheduler job — polls for deliveries that are due for (re)delivery.
    Runs every 15 seconds.
    """
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status.in_([DeliveryStatus.PENDING, DeliveryStatus.RETRYING]),
                WebhookDelivery.next_retry_at <= now,
            ).order_by(WebhookDelivery.created_at).limit(50)
        )
        deliveries = result.scalars().all()

        if not deliveries:
            return

        log.info("webhook.worker.processing", count=len(deliveries))
        for delivery in deliveries:
            await deliver_webhook(db, delivery)
        await db.commit()


async def enqueue_webhook(
    db: AsyncSession,
    client_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> WebhookDelivery | None:
    """
    Create a pending webhook delivery record for a client.
    Returns None if the client is not subscribed to this event.
    """
    client = await db.get(IntegrationClient, client_id)
    if not client or not client.webhook_url:
        return None
    if event_type not in client.webhook_events:
        return None

    delivery = WebhookDelivery(
        client_id  = client_id,
        event_type = event_type,
        payload    = payload,
        status     = DeliveryStatus.PENDING,
        next_retry_at = datetime.utcnow(),   # deliver immediately on next poll
    )
    db.add(delivery)
    return delivery
