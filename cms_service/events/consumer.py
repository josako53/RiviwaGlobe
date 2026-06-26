"""
events/consumer.py — CMS Kafka consumer for riviwa.organisation.events.

Reacts to org lifecycle events that require bulk archiving of published content:
  - organisation.suspended  → archive all PUBLISHED / SCHEDULED / IN_REVIEW posts
  - organisation.banned     → same
  - organisation.deactivated → same

Posts that are already DRAFT or ARCHIVED are left untouched.
Re-publishing archived posts when an org is restored is a deliberate human
decision — the consumer does NOT auto-restore on status recovery.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import update

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import KafkaTopics
from models.post import OrgPost, PostStatus

log = structlog.get_logger(__name__)

_consumer_task: Optional[asyncio.Task] = None

_ORG_SUSPEND_EVENTS = {
    "organisation.suspended",
    "organisation.banned",
    "organisation.deactivated",
}

_ARCHIVABLE_STATUSES = {
    PostStatus.PUBLISHED,
    PostStatus.SCHEDULED,
    PostStatus.IN_REVIEW,
}

_RETRY_DELAYS = [2, 4, 8, 16, 30, 60]


async def _archive_org_posts(org_id: uuid.UUID, event_type: str, reason: Optional[str]) -> None:
    """Bulk-archive all active posts for the given org."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(OrgPost)
            .where(
                OrgPost.org_id == org_id,
                OrgPost.status.in_(_ARCHIVABLE_STATUSES),
                OrgPost.deleted_at.is_(None),
            )
            .values(status=PostStatus.ARCHIVED)
            .returning(OrgPost.id)
        )
        archived_ids = result.fetchall()
        await session.commit()

    log.info(
        "cms.org_posts.archived",
        org_id=str(org_id),
        event_type=event_type,
        reason=reason,
        count=len(archived_ids),
    )


async def _handle_event(msg: dict) -> None:
    event_type = msg.get("event_type", "")
    if event_type not in _ORG_SUSPEND_EVENTS:
        return

    payload = msg.get("payload", {})
    raw_org_id = payload.get("org_id")
    if not raw_org_id:
        log.warning("cms.consumer.missing_org_id", event_type=event_type)
        return

    try:
        org_id = uuid.UUID(raw_org_id)
    except ValueError:
        log.warning("cms.consumer.invalid_org_id", raw=raw_org_id)
        return

    reason = payload.get("reason")
    await _archive_org_posts(org_id, event_type, reason)


async def _consume_loop() -> None:
    attempt = 0
    while True:
        consumer = AIOKafkaConsumer(
            KafkaTopics.ORG_EVENTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            retry_backoff_ms=1000,
            connections_max_idle_ms=30_000,
            request_timeout_ms=15_000,
        )
        try:
            await consumer.start()
            attempt = 0
            log.info("cms.consumer.started", topic=KafkaTopics.ORG_EVENTS)
            async for msg in consumer:
                try:
                    await _handle_event(msg.value)
                except Exception as exc:
                    log.error(
                        "cms.consumer.handle_error",
                        error=str(exc),
                        exc_info=exc,
                        offset=msg.offset,
                    )
        except asyncio.CancelledError:
            log.info("cms.consumer.cancelled")
            break
        except Exception as exc:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            log.warning(
                "cms.consumer.error",
                error=str(exc),
                retry_in=delay,
                attempt=attempt,
            )
            attempt += 1
            await asyncio.sleep(delay)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop(), name="cms_org_consumer")
    log.info("cms.consumer.task_created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    log.info("cms.consumer.task_stopped")
