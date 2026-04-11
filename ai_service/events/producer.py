"""events/producer.py — ai_service Kafka producer."""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import structlog
from aiokafka import AIOKafkaProducer
from core.config import settings
from events.topics import KafkaTopics

log = structlog.get_logger(__name__)
_producer: Optional["AIProducer"] = None
_producer_lock = asyncio.Lock()


class AIProducer:
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
        log.info("ai.producer.started")

    async def stop(self) -> None:
        if self._p:
            await self._p.stop()
            self._p = None

    def _env(self, event_type: str, payload: dict) -> dict:
        return {
            "event_type": event_type,
            "event_id":   str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service": settings.AI_SERVICE_NAME,
            "payload": payload,
        }

    async def publish(self, topic: str, event_type: str, payload: dict,
                      key: Optional[str] = None) -> None:
        if not self._p:
            return
        try:
            await self._p.send_and_wait(topic, value=self._env(event_type, payload), key=key)
        except Exception as exc:
            log.error("ai.producer.failed", event_type=event_type, error=str(exc))

    async def notify_sms(self, phone: str, message: str) -> None:
        """Publish to notifications topic so notification_service sends SMS."""
        await self.publish(
            KafkaTopics.NOTIFICATIONS,
            "ai.sms_reply",
            {
                "notification_type": "ai_sms_reply",
                "recipient": {"phone": phone},
                "channels": ["sms"],
                "variables": {"message": message},
            },
            key=phone,
        )

    async def notify_whatsapp(self, whatsapp_id: str, message: str) -> None:
        """Publish to notifications topic so notification_service sends WhatsApp message."""
        await self.publish(
            KafkaTopics.NOTIFICATIONS,
            "ai.whatsapp_reply",
            {
                "notification_type": "ai_whatsapp_reply",
                "recipient": {"whatsapp": whatsapp_id},
                "channels": ["whatsapp"],
                "variables": {"message": message},
            },
            key=whatsapp_id,
        )


async def get_producer() -> AIProducer:
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            _producer = AIProducer()
            await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
