"""events/subscription_consumer.py — Durable notification consumer for riviwa.subscription.events."""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import httpx
import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings
from db.session import AsyncSessionLocal
from services.delivery_service import DeliveryService

log = structlog.get_logger(__name__)

SUBSCRIPTION_TOPIC = "riviwa.subscription.events"
GROUP_ID = "notification_service_subscription_events"

_consumer_task: Optional[asyncio.Task] = None
_RETRY_DELAYS = [2, 4, 8, 16, 30, 60]

_SVC_HEADERS = {"X-Service-Key": settings.INTERNAL_SERVICE_KEY}


async def _get_owner_contact(org_id: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/orgs/{org_id}/owner-contact",
                headers=_SVC_HEADERS,
            )
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        log.warning("subscription_consumer.owner_contact_failed", org_id=org_id, error=str(exc))
    return None


def _build_envelope(event_type: str, payload: dict, contact: dict) -> Optional[dict]:
    org_id = payload.get("org_id", "")
    owner_name = contact.get("display_name") or contact.get("org_name", "")
    org_name = contact.get("org_name", "")
    base = {
        "recipient_user_id": contact.get("user_id"),
        "recipient_email": contact.get("email"),
        "recipient_phone": contact.get("phone"),
        "language": contact.get("language", "en"),
        "source_service": "subscription_service",
        "source_entity_id": org_id,
    }

    if event_type == "subscription.subscribed":
        invoice_number = payload.get("invoice_number", "")
        return {**base,
            "notification_type": "subscription.subscribed",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "plan_name": payload.get("plan", ""),
                "billing_cycle": payload.get("billing_cycle", ""),
                "invoice_number": invoice_number,
            },
            "preferred_channels": ["email", "in_app"],
            "priority": "high",
            "idempotency_key": f"subscribed:{org_id}:{invoice_number}",
        }

    if event_type == "subscription.upgraded":
        to_plan = payload.get("to_plan", "")
        return {**base,
            "notification_type": "subscription.upgraded",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "old_plan": payload.get("from_plan", ""),
                "new_plan": to_plan,
            },
            "preferred_channels": ["email", "in_app"],
            "priority": "high",
            "idempotency_key": f"upgraded:{org_id}:{to_plan}",
        }

    if event_type == "subscription.downgraded":
        to_plan = payload.get("to_plan", "")
        return {**base,
            "notification_type": "subscription.downgraded",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "old_plan": payload.get("from_plan", ""),
                "new_plan": to_plan,
                "effective_date": payload.get("effective_date", ""),
            },
            "preferred_channels": ["email", "in_app"],
            "priority": "medium",
            "idempotency_key": f"downgraded:{org_id}:{to_plan}",
        }

    if event_type == "subscription.cancelled":
        return {**base,
            "notification_type": "subscription.cancelled",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "plan_name": payload.get("plan_name", "your plan"),
                "access_end_date": payload.get("access_end_date", ""),
            },
            "preferred_channels": ["email", "in_app"],
            "priority": "high",
            "idempotency_key": f"cancelled:{org_id}",
        }

    if event_type == "subscription.payment_succeeded":
        invoice_number = payload.get("invoice_number", "")
        return {**base,
            "notification_type": "subscription.payment_receipt",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "invoice_number": invoice_number,
                "amount_usd": payload.get("amount_usd", ""),
            },
            "preferred_channels": ["email", "in_app"],
            "priority": "high",
            "idempotency_key": f"receipt:{invoice_number}",
        }

    if event_type == "subscription.payment_failed":
        invoice_number = payload.get("invoice_number", "")
        return {**base,
            "notification_type": "subscription.payment_failed",
            "variables": {
                "owner_name": owner_name, "org_name": org_name,
                "invoice_number": invoice_number,
                "failure_reason": payload.get("failure_reason", "Payment declined"),
            },
            "preferred_channels": ["email", "push", "in_app"],
            "priority": "high",
            "idempotency_key": f"pay_failed:{invoice_number}",
        }

    return None


async def _handle_event(msg: dict) -> None:
    event_type = msg.get("event_type", "")
    payload = msg.get("payload", {})
    org_id = payload.get("org_id")

    if not org_id:
        return

    contact = await _get_owner_contact(org_id)
    if not contact:
        log.warning("subscription_consumer.no_contact", org_id=org_id, event_type=event_type)
        return

    envelope = _build_envelope(event_type, payload, contact)
    if envelope is None:
        return

    async with AsyncSessionLocal() as db:
        svc = DeliveryService(db)
        notif_id = await svc.process_request(envelope)
        if notif_id:
            log.info("subscription_consumer.dispatched",
                     notification_type=envelope["notification_type"],
                     org_id=org_id, id=str(notif_id))


async def _consume_loop() -> None:
    attempt = 0
    while True:
        consumer = AIOKafkaConsumer(
            SUBSCRIPTION_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            retry_backoff_ms=1000,
            connections_max_idle_ms=30_000,
            request_timeout_ms=15_000,
        )
        try:
            await consumer.start()
            attempt = 0
            log.info("subscription_consumer.started", topic=SUBSCRIPTION_TOPIC)
            async for msg in consumer:
                try:
                    await _handle_event(msg.value)
                except Exception as exc:
                    log.error("subscription_consumer.handle_error",
                              error=str(exc), exc_info=exc, offset=msg.offset)
        except asyncio.CancelledError:
            log.info("subscription_consumer.cancelled")
            break
        except Exception as exc:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            log.warning("subscription_consumer.error",
                        error=str(exc), retry_in=delay, attempt=attempt)
            attempt += 1
            await asyncio.sleep(delay)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass


async def start_subscription_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop(), name="subscription_events_consumer")
    log.info("subscription_consumer.task_created")


async def stop_subscription_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    log.info("subscription_consumer.task_stopped")
