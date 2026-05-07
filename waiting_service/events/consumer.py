from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import KafkaTopics
from models.org_cache import OrgCache
from models.queue_ticket import QueueTicket, TicketPriority, TicketStatus

log = structlog.get_logger(__name__)
_consumer_task: Optional[asyncio.Task] = None

_ORG_EVENTS = frozenset({
    "organisation.created", "organisation.updated",
    "organisation.verified", "organisation.suspended",
    "organisation.deactivated", "organisation.banned",
})


async def _handle_org_event(payload: dict, event_type: str) -> None:
    raw_org_id = payload.get("org_id") or payload.get("id")
    name = payload.get("name") or payload.get("display_name") or payload.get("legal_name") or ""
    slug = payload.get("slug") or ""
    if not raw_org_id:
        return
    try:
        org_id = uuid.UUID(str(raw_org_id))
    except ValueError:
        return

    is_active = event_type not in ("organisation.suspended", "organisation.deactivated", "organisation.banned")
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(OrgCache).where(OrgCache.org_id == org_id))
            existing = result.scalar_one_or_none()
            if existing:
                if name:
                    existing.name = name
                if slug:
                    existing.slug = slug
                existing.is_active = is_active
                existing.synced_at = now
                db.add(existing)
            else:
                db.add(OrgCache(org_id=org_id, name=name, slug=slug, is_active=is_active, synced_at=now))
            await db.commit()
            log.info("waiting.consumer.org_cache.upserted", org_id=str(org_id), event_type=event_type)
        except Exception as exc:
            await db.rollback()
            log.error("waiting.consumer.org_cache.error", error=str(exc))


async def _handle_feedback_event(payload: dict, event_type: str) -> None:
    """Auto-escalate linked WAITING ticket to URGENT when feedback.escalated fires."""
    if event_type != "feedback.escalated":
        log.debug("waiting.consumer.feedback.ignored", event_type=event_type)
        return
    external_id = payload.get("external_id")
    if not external_id:
        return

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(QueueTicket).where(
                    QueueTicket.external_id == external_id,
                    QueueTicket.status == TicketStatus.WAITING,
                ).limit(1)
            )
            ticket = result.scalar_one_or_none()
            if not ticket or ticket.priority == TicketPriority.URGENT:
                return
            old_priority = ticket.priority
            ticket.priority = TicketPriority.URGENT
            ticket.updated_at = datetime.now(timezone.utc)
            db.add(ticket)
            await db.commit()
            log.info("waiting.consumer.feedback.ticket_escalated",
                     ticket_number=ticket.ticket_number, old_priority=old_priority)
            # Publish priority_changed event
            from events.producer import get_producer
            producer = await get_producer()
            await producer.ticket_priority_changed(
                ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
                old_priority=old_priority, new_priority=TicketPriority.URGENT,
                phone_number=ticket.phone_number,
                reason="Auto-escalated: linked GRM feedback escalated",
            )
        except Exception as exc:
            log.error("waiting.consumer.feedback.error", error=str(exc))


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        KafkaTopics.ORG_EVENTS,
        KafkaTopics.FEEDBACK_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="waiting_service_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    log.info("waiting.consumer.started")
    try:
        async for msg in consumer:
            event_type = msg.value.get("event_type", "")
            payload = msg.value.get("payload", {})
            try:
                if event_type in _ORG_EVENTS:
                    await _handle_org_event(payload, event_type)
                elif event_type.startswith("feedback."):
                    await _handle_feedback_event(payload, event_type)
                else:
                    log.debug("waiting.consumer.unhandled", event_type=event_type)
            except Exception as exc:
                log.error("waiting.consumer.message_error", event_type=event_type, error=str(exc))
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
        log.info("waiting.consumer.stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
