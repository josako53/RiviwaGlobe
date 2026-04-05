"""
events/producer.py
═══════════════════════════════════════════════════════════════════════════════
Async Kafka producer singleton for stakeholder_service.
Same pattern as auth_service/workers/kafka_producer.py.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import KafkaTopics, StakeholderEvents

log = structlog.get_logger(__name__)

_producer: Optional["StakeholderProducer"] = None
_producer_lock = asyncio.Lock()


class StakeholderProducer:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            retry_backoff_ms=200,
            compression_type="zstd",
            linger_ms=5,
            request_timeout_ms=15_000,
        )
        await self._producer.start()
        log.info("stakeholder.kafka_producer.started")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None
            log.info("stakeholder.kafka_producer.stopped")

    def _envelope(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_type":     event_type,
            "event_id":       str(uuid.uuid4()),
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service":        settings.STAKEHOLDER_SERVICE_NAME,
            "payload":        payload,
        }

    async def publish(
        self,
        topic:      str,
        event_type: str,
        payload:    dict[str, Any],
        key:        Optional[str] = None,
    ) -> None:
        if not self._producer:
            log.warning("stakeholder.kafka_producer.not_started", topic=topic)
            return
        try:
            envelope = self._envelope(event_type, payload)
            await self._producer.send_and_wait(topic, value=envelope, key=key)
            log.debug("stakeholder.kafka_producer.published", topic=topic, event_type=event_type)
        except Exception as exc:
            log.error("stakeholder.kafka_producer.failed", topic=topic, error=str(exc))
            # Fire-and-forget: never abort the request due to Kafka failure

    # ── Typed publish helpers ─────────────────────────────────────────────────

    async def stakeholder_registered(self, stakeholder_id: uuid.UUID, entity_type: str, category: str) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.REGISTERED,
            {"stakeholder_id": str(stakeholder_id), "entity_type": entity_type, "category": category},
            key=str(stakeholder_id),
        )

    async def stakeholder_updated(self, stakeholder_id: uuid.UUID, changed_fields: list[str]) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.UPDATED,
            {"stakeholder_id": str(stakeholder_id), "changed_fields": changed_fields},
            key=str(stakeholder_id),
        )

    async def contact_added(self, stakeholder_id: uuid.UUID, contact_id: uuid.UUID, is_primary: bool) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.CONTACT_ADDED,
            {"stakeholder_id": str(stakeholder_id), "contact_id": str(contact_id), "is_primary": is_primary},
            key=str(stakeholder_id),
        )

    async def activity_conducted(
        self,
        activity_id: uuid.UUID,
        project_id:  uuid.UUID,
        stage:       str,
        actual_count: Optional[int],
    ) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.ACTIVITY_CONDUCTED,
            {
                "activity_id":   str(activity_id),
                "project_id":    str(project_id),
                "stage":         stage,
                "actual_count":  actual_count,
            },
            key=str(project_id),
        )

    async def concern_raised(
        self,
        activity_id:    uuid.UUID,
        contact_id:     uuid.UUID,
        stakeholder_id: uuid.UUID,
        project_id:     uuid.UUID,
        concerns:       str,
    ) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.CONCERN_RAISED,
            {
                "activity_id":    str(activity_id),
                "contact_id":     str(contact_id),
                "stakeholder_id": str(stakeholder_id),
                "project_id":     str(project_id),
                "concerns":       concerns,
            },
            key=str(project_id),
        )

    async def comm_concerns_pending(
        self,
        distribution_id: uuid.UUID,
        comm_id:         uuid.UUID,
        contact_id:      uuid.UUID,
        project_id:      uuid.UUID,
        concerns:        str,
    ) -> None:
        await self.publish(
            KafkaTopics.STAKEHOLDER_EVENTS,
            StakeholderEvents.COMM_CONCERNS_PENDING,
            {
                "distribution_id": str(distribution_id),
                "comm_id":         str(comm_id),
                "contact_id":      str(contact_id),
                "project_id":      str(project_id),
                "concerns":        concerns,
            },
            key=str(project_id),
        )


async def get_producer() -> StakeholderProducer:
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            _producer = StakeholderProducer()
            await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
