"""events/producer.py"""
from __future__ import annotations
import asyncio, json, uuid
from datetime import datetime, timezone
from typing import Any, Optional
import structlog
from aiokafka import AIOKafkaProducer
from core.config import settings
from events.topics import KafkaTopics, FeedbackEvents

log = structlog.get_logger(__name__)
_producer: Optional["FeedbackProducer"] = None
_producer_lock = asyncio.Lock()


class FeedbackProducer:
    def __init__(self) -> None:
        self._p: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._p = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all", enable_idempotence=True, compression_type="zstd",
            linger_ms=5, request_timeout_ms=15_000,
        )
        await self._p.start()
        log.info("feedback.producer.started")

    async def stop(self) -> None:
        if self._p:
            await self._p.stop()
            self._p = None

    def _env(self, event_type: str, payload: dict) -> dict:
        return {
            "event_type": event_type, "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0", "service": settings.FEEDBACK_SERVICE_NAME,
            "payload": payload,
        }

    async def publish(self, event_type: str, payload: dict, key: Optional[str] = None) -> None:
        if not self._p:
            return
        try:
            await self._p.send_and_wait(KafkaTopics.FEEDBACK_EVENTS, value=self._env(event_type, payload), key=key)
        except Exception as exc:
            log.error("feedback.producer.failed", event_type=event_type, error=str(exc))

    # ── Typed helpers ──────────────────────────────────────────────────────────

    async def feedback_submitted(self, feedback_id: uuid.UUID, project_id: uuid.UUID,
                                  feedback_type: str, category: str,
                                  org_id: Optional[uuid.UUID] = None,
                                  branch_id: Optional[uuid.UUID] = None,
                                  department_id: Optional[uuid.UUID] = None,
                                  stakeholder_engagement_id: Optional[uuid.UUID] = None,
                                  distribution_id: Optional[uuid.UUID] = None) -> None:
        await self.publish(FeedbackEvents.SUBMITTED, {
            "feedback_id":   str(feedback_id),
            "project_id":    str(project_id),
            "feedback_type": feedback_type,
            "category":      category,
            "org_id":        str(org_id)        if org_id        else None,
            "branch_id":     str(branch_id)     if branch_id     else None,
            "department_id": str(department_id) if department_id else None,
            "stakeholder_engagement_id": str(stakeholder_engagement_id) if stakeholder_engagement_id else None,
            "distribution_id":           str(distribution_id)           if distribution_id           else None,
        }, key=str(project_id))

    async def feedback_acknowledged(self, feedback_id: uuid.UUID, project_id: uuid.UUID,
                                     priority: str,
                                     branch_id: Optional[uuid.UUID] = None,
                                     department_id: Optional[uuid.UUID] = None) -> None:
        await self.publish(FeedbackEvents.ACKNOWLEDGED, {
            "feedback_id":   str(feedback_id),
            "project_id":    str(project_id),
            "priority":      priority,
            "branch_id":     str(branch_id)     if branch_id     else None,
            "department_id": str(department_id) if department_id else None,
        }, key=str(project_id))

    async def feedback_escalated(self, feedback_id: uuid.UUID, project_id: uuid.UUID,
                                  from_level: str, to_level: str, reason: str,
                                  branch_id: Optional[uuid.UUID] = None,
                                  department_id: Optional[uuid.UUID] = None) -> None:
        await self.publish(FeedbackEvents.ESCALATED, {
            "feedback_id":   str(feedback_id),
            "project_id":    str(project_id),
            "from_level":    from_level,
            "to_level":      to_level,
            "reason":        reason,
            "branch_id":     str(branch_id)     if branch_id     else None,
            "department_id": str(department_id) if department_id else None,
        }, key=str(project_id))

    async def feedback_resolved(self, feedback_id: uuid.UUID, project_id: uuid.UUID,
                                 branch_id: Optional[uuid.UUID] = None,
                                 department_id: Optional[uuid.UUID] = None) -> None:
        await self.publish(FeedbackEvents.RESOLVED, {
            "feedback_id":   str(feedback_id),
            "project_id":    str(project_id),
            "branch_id":     str(branch_id)     if branch_id     else None,
            "department_id": str(department_id) if department_id else None,
        }, key=str(project_id))

    async def feedback_appealed(self, feedback_id: uuid.UUID, project_id: uuid.UUID,
                                 grounds: str,
                                 branch_id: Optional[uuid.UUID] = None,
                                 department_id: Optional[uuid.UUID] = None) -> None:
        await self.publish(FeedbackEvents.APPEALED, {
            "feedback_id":   str(feedback_id),
            "project_id":    str(project_id),
            "grounds":       grounds,
            "branch_id":     str(branch_id)     if branch_id     else None,
            "department_id": str(department_id) if department_id else None,
        }, key=str(project_id))


async def get_producer() -> FeedbackProducer:
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            _producer = FeedbackProducer()
            await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
