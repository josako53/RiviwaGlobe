# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  events/consumer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/consumer.py
═══════════════════════════════════════════════════════════════════════════════
Kafka consumer for the riviwa.notifications topic.

All other services publish notification requests here.
This consumer is the primary intake for the notification service.

Message envelope format (published by originating services):
{
  "event_type":           "notification.request",
  "notification_type":    "grm.feedback.acknowledged",
  "recipient_user_id":    "uuid|null",
  "recipient_phone":      "+255...|null",
  "recipient_email":      "user@example.com|null",
  "recipient_push_tokens": [],        # optional, client-supplied override
  "language":             "sw",
  "variables":            { ... },    # template rendering variables
  "preferred_channels":   ["push", "sms"],
  "priority":             "high",
  "idempotency_key":      "feedback:uuid:acknowledged:2025-06-15",
  "scheduled_at":         null,       # null = immediate, ISO datetime = reminder
  "source_service":       "feedback_service",
  "source_entity_id":     "uuid",
  "metadata":             { ... }
}

The notification_service is IGNORANT of the business meaning.
It processes whatever comes in, looks up the template, and delivers.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import structlog
from typing import Optional

from aiokafka import AIOKafkaConsumer

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import KafkaTopics
from services.delivery_service import DeliveryService

log = structlog.get_logger(__name__)

_consumer_task: Optional[asyncio.Task] = None


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        KafkaTopics.NOTIFICATIONS,
        bootstrap_servers     = settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id              = "notification_service_group",
        auto_offset_reset     = "earliest",
        enable_auto_commit    = True,
        value_deserializer    = lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    log.info("notification.consumer.started",
             topic=KafkaTopics.NOTIFICATIONS)
    try:
        async for msg in consumer:
            try:
                await _handle(msg.value)
            except Exception as exc:
                log.error("notification.consumer.handler_error",
                          error=str(exc), msg=str(msg.value)[:200])
    finally:
        await consumer.stop()
        log.info("notification.consumer.stopped")


async def _handle(envelope: dict) -> None:
    """
    Process one notification request message.

    Validates the minimal required fields and hands off to DeliveryService.
    Unknown fields are passed through and will be ignored by the service.
    """
    notification_type = envelope.get("notification_type", "")
    if not notification_type:
        log.warning("notification.consumer.missing_type", envelope=str(envelope)[:200])
        return

    async with AsyncSessionLocal() as db:
        svc = DeliveryService(db)
        notif_id = await svc.process_request(envelope)
        if notif_id:
            log.debug("notification.consumer.processed",
                      id=str(notif_id),
                      notification_type=notification_type)


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    log.info("notification.consumer.task_created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
    log.info("notification.consumer.task_stopped")
