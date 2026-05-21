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


_RETRY_DELAYS = [2, 4, 8, 16, 30, 60]  # seconds — exponential backoff cap at 60s


async def _consume_loop() -> None:
    """
    Kafka consumer loop with reconnect backoff.

    If consumer.start() fails (Kafka unavailable at startup) or the consume
    loop crashes (broker restart, network blip), we wait with exponential
    backoff before retrying.  The backoff yields the event loop between
    attempts so uvicorn can keep serving HTTP requests while Kafka is down.
    """
    attempt = 0
    while True:
        consumer = AIOKafkaConsumer(
            KafkaTopics.NOTIFICATIONS,
            bootstrap_servers        = settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id                 = "notification_service_group",
            auto_offset_reset        = "earliest",
            enable_auto_commit       = True,
            value_deserializer       = lambda v: json.loads(v.decode("utf-8")),
            retry_backoff_ms         = 1000,   # 1 s between internal retries
            connections_max_idle_ms  = 30_000, # drop idle connections after 30 s
            request_timeout_ms       = 15_000, # don't wait >15 s per request
        )
        try:
            # Timeout prevents consumer.start() from blocking the event loop
            # indefinitely when Kafka is slow to respond after a broker restart.
            await asyncio.wait_for(consumer.start(), timeout=15)
            attempt = 0  # reset on successful connect
            log.info("notification.consumer.started", topic=KafkaTopics.NOTIFICATIONS)
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
        except asyncio.CancelledError:
            # Graceful shutdown — do not retry
            try:
                await consumer.stop()
            except Exception:
                pass
            log.info("notification.consumer.cancelled")
            return
        except Exception as exc:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            log.warning(
                "notification.consumer.reconnecting",
                error=str(exc),
                retry_in_seconds=delay,
                attempt=attempt + 1,
            )
            attempt += 1
            # Yield the event loop so uvicorn can serve requests during backoff
            await asyncio.sleep(delay)


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
