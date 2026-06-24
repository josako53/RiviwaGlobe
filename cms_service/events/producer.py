from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional
import structlog
from aiokafka import AIOKafkaProducer
from core.config import settings
from events.topics import KafkaTopics

log = structlog.get_logger(__name__)
_producer: Optional[AIOKafkaProducer] = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
    return _producer


async def publish_cms_event(event_type: str, payload: dict, key: str | None = None) -> None:
    try:
        producer = await get_producer()
        envelope = {
            "event_type": event_type,
            "service":    "cms_service",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "payload":    payload,
        }
        await producer.send_and_wait(
            KafkaTopics.CMS_EVENTS,
            value=envelope,
            key=key.encode("utf-8") if key else None,
        )
        log.info("cms.event_published", event_type=event_type, key=key)
    except Exception as exc:
        log.error("cms.event_publish_failed", event_type=event_type, error=str(exc))
