"""events/consumer.py — Kafka consumer: mark QR codes used on feedback submission."""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings

log = structlog.get_logger(__name__)
_consumer: AIOKafkaConsumer | None = None


async def start_consumer() -> None:
    global _consumer
    try:
        _consumer = AIOKafkaConsumer(
            settings.KAFKA_FEEDBACK_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode()),
        )
        await _consumer.start()
        asyncio.create_task(_consume_loop())
        log.info("qr_consumer.started", topic=settings.KAFKA_FEEDBACK_TOPIC)
    except Exception as exc:
        log.warning("qr_consumer.start_failed", error=str(exc))


async def stop_consumer() -> None:
    global _consumer
    if _consumer:
        try:
            await _consumer.stop()
        except Exception:
            pass
        _consumer = None


async def _consume_loop() -> None:
    global _consumer
    if not _consumer:
        return
    from db.session import AsyncSessionLocal
    from repositories.qr_repo import QRRepository

    async for msg in _consumer:
        try:
            event = msg.value
            # feedback.submitted events carry short_code and feedback_id
            if event.get("event_type") not in ("feedback.submitted", "FEEDBACK_SUBMITTED"):
                continue
            short_code  = event.get("short_code") or event.get("qr_code")
            feedback_id_str = event.get("feedback_id")
            if not short_code:
                continue
            feedback_id = uuid.UUID(feedback_id_str) if feedback_id_str else None

            async with AsyncSessionLocal() as db:
                repo = QRRepository(db)
                ok = await repo.mark_feedback(short_code, feedback_id)
                if ok:
                    await db.commit()
                    log.info("qr_consumer.marked", short_code=short_code)
        except Exception as exc:
            log.error("qr_consumer.error", error=str(exc))
