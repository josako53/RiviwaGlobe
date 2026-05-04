from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings
from db.session import AsyncSessionLocal
from repositories.product_repo import ProductRepository

log = structlog.get_logger(__name__)

_consumer_task: Optional[asyncio.Task] = None


async def _handle_org_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Sync org cache from auth_service organisation events."""
    org_id_raw = payload.get("organisation_id") or payload.get("org_id")
    if not org_id_raw:
        return
    try:
        org_id = UUID(str(org_id_raw))
    except ValueError:
        return

    async with AsyncSessionLocal() as db:
        repo = ProductRepository(db)
        try:
            if event_type in (
                "organisation.created",
                "organisation.updated",
                "organisation.verified",
            ):
                await repo.upsert_org_cache(org_id, {
                    "name": payload.get("name", ""),
                    "slug": payload.get("slug"),
                    "is_active": True,
                    "is_verified": event_type == "organisation.verified",
                    "synced_at": datetime.utcnow(),
                })
            elif event_type in (
                "organisation.suspended",
                "organisation.banned",
                "organisation.deactivated",
            ):
                await repo.upsert_org_cache(org_id, {
                    "name": payload.get("name", ""),
                    "slug": payload.get("slug"),
                    "is_active": False,
                    "is_verified": False,
                    "synced_at": datetime.utcnow(),
                })
            await db.commit()
            log.info("product.consumer.org_synced", event_type=event_type, org_id=str(org_id))
        except Exception as exc:
            await db.rollback()
            log.error("product.consumer.org_sync_failed", event_type=event_type, error=str(exc))


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        settings.KAFKA_ORG_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    await consumer.start()
    log.info("product.kafka_consumer.started", topics=[settings.KAFKA_ORG_TOPIC])
    try:
        async for msg in consumer:
            try:
                envelope = msg.value
                event_type = envelope.get("event_type", "")
                payload = envelope.get("payload", {})
                if event_type.startswith("organisation."):
                    await _handle_org_event(event_type, payload)
            except Exception as exc:
                log.error("product.consumer.message_error", error=str(exc))
    finally:
        await consumer.stop()
        log.info("product.kafka_consumer.stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    log.info("product.consumer.task_created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
