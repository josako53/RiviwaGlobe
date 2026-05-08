"""events/consumer.py — Kafka consumer for staff_service.

Listens to riviwa.organisation.events and syncs the local OrgCache table.
"""
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
from repositories.org_cache_repository import OrgCacheRepository

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
        repo = OrgCacheRepository(db)
        try:
            if event_type in (
                "organisation.created",
                "organisation.updated",
                "organisation.verified",
            ):
                await repo.upsert(org_id, {
                    "name": payload.get("name", ""),
                    "slug": payload.get("slug"),
                    "is_active": True,
                    "synced_at": datetime.utcnow(),
                })
            elif event_type in (
                "organisation.suspended",
                "organisation.banned",
                "organisation.deactivated",
            ):
                await repo.upsert(org_id, {
                    "name": payload.get("name", ""),
                    "slug": payload.get("slug"),
                    "is_active": False,
                    "synced_at": datetime.utcnow(),
                })
            await db.commit()
            log.info("staff.consumer.org_synced", event_type=event_type, org_id=str(org_id))
        except Exception as exc:
            await db.rollback()
            log.error("staff.consumer.org_sync_failed", event_type=event_type, error=str(exc))


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
    log.info("staff.kafka_consumer.started", topics=[settings.KAFKA_ORG_TOPIC])
    try:
        async for msg in consumer:
            try:
                envelope = msg.value
                event_type = envelope.get("event_type", "")
                payload = envelope.get("payload", {})
                if event_type.startswith("organisation."):
                    await _handle_org_event(event_type, payload)
            except Exception as exc:
                log.error("staff.consumer.message_error", error=str(exc))
    finally:
        await consumer.stop()
        log.info("staff.kafka_consumer.stopped")


async def start_consumer() -> None:
    global _consumer_task
    try:
        _consumer_task = asyncio.create_task(_consume_loop())
        log.info("staff.consumer.task_created")
    except Exception as exc:
        log.warning("staff.consumer.start_failed", error=str(exc))


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
