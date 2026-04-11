# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  events/producer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/producer.py
═══════════════════════════════════════════════════════════════════════════════
Kafka producer for the notification_service.

Publishes delivery receipt events to: riviwa.notifications.events

These events allow originating services (feedback_service, auth_service, etc.)
to react to delivery outcomes — e.g. update a "notification sent" audit flag,
trigger a fallback action when SMS fails, or record when a user reads a message.

Event envelope format:
{
  "event_type":        "notification.delivered" | "notification.failed" | "notification.read",
  "notification_id":   "uuid",
  "delivery_id":       "uuid",
  "notification_type": "grm.feedback.acknowledged",
  "channel":           "sms",
  "recipient_user_id": "uuid | null",
  "source_entity_id":  "uuid | null",
  "source_service":    "feedback_service | null",
  "provider":          "africas_talking | twilio | fcm | sendgrid | meta_cloud | in_app",
  "provider_message_id": "...",
  "status":            "sent | delivered | failed | read | skipped",
  "failure_reason":    "...",
  "occurred_at":       "ISO-8601 datetime",
  "metadata":          {}
}

The producer is a singleton started at app lifespan and injected into
DeliveryService via dependency injection.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import KafkaTopics

log = structlog.get_logger(__name__)

# Module-level singleton — started in main.py lifespan
_producer: Optional[AIOKafkaProducer] = None


async def start_producer() -> None:
    """Start the Kafka producer. Called once at app startup."""
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        compression_type="gzip",
        acks="all",                   # wait for all in-sync replicas
        enable_idempotence=True,      # exactly-once semantics
        max_batch_size=16384,
        linger_ms=5,                  # small batch window for throughput
    )
    await _producer.start()
    log.info("notification_producer.started",
             brokers=settings.KAFKA_BOOTSTRAP_SERVERS)


async def stop_producer() -> None:
    """Flush and stop the Kafka producer. Called at app shutdown."""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        log.info("notification_producer.stopped")


def get_producer() -> Optional[AIOKafkaProducer]:
    return _producer


# ─────────────────────────────────────────────────────────────────────────────
# NotificationPublisher
# ─────────────────────────────────────────────────────────────────────────────

class NotificationPublisher:
    """
    Publishes delivery receipt events to riviwa.notifications.events.

    Each method corresponds to a lifecycle state change of a delivery attempt.
    Partition key = recipient_user_id (or notification_id as fallback) to
    guarantee ordering per user.
    """

    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._p = producer

    # ── Public helpers ────────────────────────────────────────────────────────

    async def delivery_sent(
        self,
        notification_id:    uuid.UUID,
        delivery_id:        uuid.UUID,
        notification_type:  str,
        channel:            str,
        recipient_user_id:  Optional[uuid.UUID],
        source_entity_id:   Optional[str],
        source_service:     Optional[str],
        provider:           Optional[str] = None,
        provider_message_id: Optional[str] = None,
        metadata:           Optional[dict] = None,
    ) -> None:
        """Published when the provider accepts the message (sent, not yet confirmed delivered)."""
        await self._publish(
            event_type="notification.sent",
            notification_id=notification_id,
            delivery_id=delivery_id,
            notification_type=notification_type,
            channel=channel,
            status="sent",
            recipient_user_id=recipient_user_id,
            source_entity_id=source_entity_id,
            source_service=source_service,
            provider=provider,
            provider_message_id=provider_message_id,
            metadata=metadata or {},
        )

    async def delivery_confirmed(
        self,
        notification_id:    uuid.UUID,
        delivery_id:        uuid.UUID,
        notification_type:  str,
        channel:            str,
        recipient_user_id:  Optional[uuid.UUID],
        source_entity_id:   Optional[str],
        source_service:     Optional[str],
        provider:           Optional[str] = None,
        provider_message_id: Optional[str] = None,
        metadata:           Optional[dict] = None,
    ) -> None:
        """Published when DLR webhook confirms the message reached the device."""
        await self._publish(
            event_type="notification.delivered",
            notification_id=notification_id,
            delivery_id=delivery_id,
            notification_type=notification_type,
            channel=channel,
            status="delivered",
            recipient_user_id=recipient_user_id,
            source_entity_id=source_entity_id,
            source_service=source_service,
            provider=provider,
            provider_message_id=provider_message_id,
            metadata=metadata or {},
        )

    async def delivery_failed(
        self,
        notification_id:   uuid.UUID,
        delivery_id:       uuid.UUID,
        notification_type: str,
        channel:           str,
        recipient_user_id: Optional[uuid.UUID],
        source_entity_id:  Optional[str],
        source_service:    Optional[str],
        failure_reason:    Optional[str] = None,
        is_permanent:      bool = False,
        provider:          Optional[str] = None,
        metadata:          Optional[dict] = None,
    ) -> None:
        """Published when a delivery attempt fails (permanent or retriable)."""
        await self._publish(
            event_type="notification.failed",
            notification_id=notification_id,
            delivery_id=delivery_id,
            notification_type=notification_type,
            channel=channel,
            status="failed",
            recipient_user_id=recipient_user_id,
            source_entity_id=source_entity_id,
            source_service=source_service,
            failure_reason=failure_reason,
            provider=provider,
            metadata={**(metadata or {}), "is_permanent": is_permanent},
        )

    async def notification_read(
        self,
        notification_id:   uuid.UUID,
        delivery_id:       uuid.UUID,
        notification_type: str,
        recipient_user_id: Optional[uuid.UUID],
        source_entity_id:  Optional[str],
        source_service:    Optional[str],
        metadata:          Optional[dict] = None,
    ) -> None:
        """Published when user marks an in-app notification as read."""
        await self._publish(
            event_type="notification.read",
            notification_id=notification_id,
            delivery_id=delivery_id,
            notification_type=notification_type,
            channel="in_app",
            status="read",
            recipient_user_id=recipient_user_id,
            source_entity_id=source_entity_id,
            source_service=source_service,
            metadata=metadata or {},
        )

    async def notification_cancelled(
        self,
        notification_id:   uuid.UUID,
        notification_type: str,
        recipient_user_id: Optional[uuid.UUID],
        source_entity_id:  Optional[str],
        source_service:    Optional[str],
        reason:            Optional[str] = None,
        metadata:          Optional[dict] = None,
    ) -> None:
        """Published when a scheduled notification is cancelled before it fires."""
        await self._publish(
            event_type="notification.cancelled",
            notification_id=notification_id,
            delivery_id=None,
            notification_type=notification_type,
            channel=None,
            status="cancelled",
            recipient_user_id=recipient_user_id,
            source_entity_id=source_entity_id,
            source_service=source_service,
            failure_reason=reason,
            metadata=metadata or {},
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _publish(
        self,
        event_type:         str,
        notification_id:    uuid.UUID,
        delivery_id:        Optional[uuid.UUID],
        notification_type:  str,
        channel:            Optional[str],
        status:             str,
        recipient_user_id:  Optional[uuid.UUID],
        source_entity_id:   Optional[str] = None,
        source_service:     Optional[str] = None,
        provider:           Optional[str] = None,
        provider_message_id: Optional[str] = None,
        failure_reason:     Optional[str] = None,
        metadata:           Optional[dict] = None,
    ) -> None:
        if not self._p:
            log.warning("notification_producer.not_started", event_type=event_type)
            return

        envelope: dict[str, Any] = {
            "event_type":           event_type,
            "notification_id":      str(notification_id),
            "delivery_id":          str(delivery_id) if delivery_id else None,
            "notification_type":    notification_type,
            "channel":              channel,
            "recipient_user_id":    str(recipient_user_id) if recipient_user_id else None,
            "source_entity_id":     source_entity_id,
            "source_service":       source_service,
            "provider":             provider,
            "provider_message_id":  provider_message_id,
            "status":               status,
            "failure_reason":       failure_reason,
            "occurred_at":          datetime.now(timezone.utc).isoformat(),
            "metadata":             metadata or {},
        }

        # Partition by user_id for per-user ordering; fall back to notification_id
        partition_key = (
            str(recipient_user_id) if recipient_user_id else str(notification_id)
        )

        try:
            await self._p.send_and_wait(
                KafkaTopics.NOTIFICATION_EVENTS,
                value=envelope,
                key=partition_key,
            )
            log.debug(
                "notification_producer.published",
                event_type=event_type,
                notification_id=str(notification_id),
                channel=channel,
                status=status,
            )
        except Exception as exc:
            # Non-fatal: delivery already recorded in DB; Kafka publish failure
            # should not break the HTTP response or consumer loop.
            log.error(
                "notification_producer.publish_failed",
                event_type=event_type,
                notification_id=str(notification_id),
                error=str(exc),
            )
