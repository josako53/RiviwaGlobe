"""events/consumer.py — Kafka consumer: activates subscriptions on payment completion."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from core.config import settings
from db.session import AsyncSessionLocal
from models.subscription import Invoice, InvoiceStatus, Subscription, SubscriptionStatus

log = structlog.get_logger(__name__)

PAYMENT_TOPIC  = "riviwa.payment.events"
GROUP_ID       = "subscription_service_payment_events"
_consumer: Optional[AIOKafkaConsumer] = None


async def start_consumer() -> None:
    global _consumer
    _consumer = AIOKafkaConsumer(
        PAYMENT_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    await _consumer.start()
    log.info("subscription.consumer.started", topic=PAYMENT_TOPIC)
    asyncio.ensure_future(_consume_loop())


async def stop_consumer() -> None:
    global _consumer
    if _consumer:
        await _consumer.stop()
        log.info("subscription.consumer.stopped")


async def _consume_loop() -> None:
    async for msg in _consumer:
        try:
            await _handle(msg.value)
        except Exception as exc:
            log.error("subscription.consumer.error", error=str(exc), offset=msg.offset)


async def _handle(event: dict) -> None:
    event_type = event.get("event_type", "")

    if event_type == "payment.completed":
        payload      = event.get("payload", {})
        reference_id = payload.get("reference_id")
        reference_type = payload.get("reference_type")

        if reference_type != "invoice" or not reference_id:
            return

        async with AsyncSessionLocal() as db:
            inv = await db.get(Invoice, uuid.UUID(reference_id))
            if not inv or inv.status == InvoiceStatus.PAID.value:
                return

            inv.status  = InvoiceStatus.PAID.value
            inv.paid_at = datetime.utcnow()
            inv.payment_reference = payload.get("payment_id", inv.payment_reference)

            sub = await db.get(Subscription, inv.subscription_id)
            if sub and sub.status in (
                SubscriptionStatus.TRIALING.value,
                SubscriptionStatus.PAST_DUE.value,
            ):
                sub.status = SubscriptionStatus.ACTIVE.value
                log.info("subscription.activated_via_payment",
                         org_id=str(sub.org_id), invoice=inv.invoice_number)

            await db.commit()

    elif event_type == "payment.failed":
        payload      = event.get("payload", {})
        reference_id = payload.get("reference_id")
        if not reference_id:
            return

        async with AsyncSessionLocal() as db:
            inv = await db.get(Invoice, uuid.UUID(reference_id))
            if inv:
                inv.retry_count += 1
                await db.commit()
                log.warning("subscription.payment_failed",
                            invoice=inv.invoice_number, retries=inv.retry_count)
