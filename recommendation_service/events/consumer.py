"""
events/consumer.py — Kafka consumer for recommendation_service.

Consumes entity and activity events from 4 topics to build and
maintain the recommendation index.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import (
    FeedbackEvents,
    KafkaTopics,
    OrgProjectEvents,
    OrgProjectStageEvents,
    StakeholderEvents,
)
from models.entity import ActivityEvent, RecommendationEntity
from repositories.entity_repository import EntityRepository
from services import embedding_service

log = structlog.get_logger(__name__)

_consumer: Optional[AIOKafkaConsumer] = None
_consumer_task: Optional[asyncio.Task] = None

# Event types we handle
_PROJECT_UPSERT = frozenset({OrgProjectEvents.PUBLISHED, OrgProjectEvents.UPDATED, OrgProjectEvents.RESUMED})
_PROJECT_DEACTIVATE = frozenset({OrgProjectEvents.PAUSED, OrgProjectEvents.COMPLETED, OrgProjectEvents.CANCELLED})
_FEEDBACK_EVENTS = frozenset({
    FeedbackEvents.SUBMITTED, FeedbackEvents.ACKNOWLEDGED,
    FeedbackEvents.ESCALATED, FeedbackEvents.RESOLVED, FeedbackEvents.CLOSED,
})
_ENGAGEMENT_EVENTS = frozenset({
    StakeholderEvents.ACTIVITY_CONDUCTED,
    StakeholderEvents.ATTENDANCE_LOGGED,
    StakeholderEvents.CONCERN_RAISED,
})


async def _handle_project_upsert(payload: dict, event_type: str) -> None:
    """Index or update a project entity from org_project events."""
    project_id = payload.get("id")
    if not project_id:
        return

    data = {
        "id": uuid.UUID(str(project_id)),
        "entity_type": "project",
        "source_service": "riviwa_auth_service",
        "organisation_id": uuid.UUID(str(payload["organisation_id"])) if payload.get("organisation_id") else None,
        "name": payload.get("name", ""),
        "slug": payload.get("slug"),
        "description": payload.get("description"),
        "category": payload.get("category"),
        "sector": payload.get("sector"),
        "country_code": payload.get("country_code"),
        "region": payload.get("region"),
        "primary_lga": payload.get("primary_lga"),
        "cover_image_url": payload.get("cover_image_url"),
        "org_logo_url": payload.get("org_logo_url"),
        "status": "active",
        "accepts_grievances": payload.get("accepts_grievances", True),
        "accepts_suggestions": payload.get("accepts_suggestions", True),
        "accepts_applause": payload.get("accepts_applause", True),
        "last_active_at": datetime.now(timezone.utc),
    }

    # Build tags from category + sector
    tag_items = []
    if data["category"]:
        tag_items.append(data["category"])
    if data["sector"]:
        tag_items.append(data["sector"])
    data["tags"] = {"items": tag_items}

    async with AsyncSessionLocal() as db:
        try:
            repo = EntityRepository(db)
            entity = await repo.upsert(data)
            await db.commit()

            # Embed and index in Qdrant
            if embedding_service.is_model_loaded():
                try:
                    text = embedding_service.build_entity_text(data)
                    th = embedding_service.text_hash(text)
                    if th != entity.embedding_text_hash:
                        vector = embedding_service.encode(text)
                        embedding_service.upsert_vector(
                            str(entity.id), vector,
                            {"entity_type": "project", "category": data.get("category"), "region": data.get("region")},
                        )
                        await repo.mark_indexed(entity.id, th)
                        await db.commit()
                except Exception as exc:
                    log.warning("rec.embed_failed", entity_id=str(project_id), error=str(exc))

            log.info("rec.project.indexed", project_id=str(project_id), event=event_type)
        except Exception as exc:
            await db.rollback()
            log.error("rec.project.upsert_failed", project_id=str(project_id), error=str(exc))


async def _handle_project_deactivate(payload: dict, event_type: str) -> None:
    """Update project status to inactive."""
    project_id = payload.get("id")
    if not project_id:
        return

    status_map = {
        OrgProjectEvents.PAUSED: "paused",
        OrgProjectEvents.COMPLETED: "completed",
        OrgProjectEvents.CANCELLED: "cancelled",
    }

    async with AsyncSessionLocal() as db:
        try:
            repo = EntityRepository(db)
            await repo.update_status(uuid.UUID(str(project_id)), status_map.get(event_type, "inactive"))
            await db.commit()
            log.info("rec.project.deactivated", project_id=str(project_id), status=event_type)
        except Exception as exc:
            await db.rollback()
            log.error("rec.project.deactivate_failed", error=str(exc))


async def _handle_feedback_event(payload: dict, event_type: str) -> None:
    """Record feedback activity and update counts."""
    project_id = payload.get("project_id")
    if not project_id:
        return

    async with AsyncSessionLocal() as db:
        try:
            repo = EntityRepository(db)
            # Add activity event
            event = ActivityEvent(
                entity_id=uuid.UUID(str(project_id)),
                event_type=event_type,
                feedback_type=payload.get("feedback_type"),
                occurred_at=datetime.now(timezone.utc),
                payload=payload,
            )
            await repo.add_activity(event)

            # Increment feedback count on the entity
            if event_type == FeedbackEvents.SUBMITTED:
                await repo.increment_feedback(
                    uuid.UUID(str(project_id)),
                    feedback_type=payload.get("feedback_type"),
                )

            await db.commit()
            log.debug("rec.feedback.recorded", project_id=str(project_id), event=event_type)
        except Exception as exc:
            await db.rollback()
            log.warning("rec.feedback.record_failed", error=str(exc))


async def _handle_engagement_event(payload: dict, event_type: str) -> None:
    """Record engagement activity."""
    project_id = payload.get("project_id")
    if not project_id:
        return

    async with AsyncSessionLocal() as db:
        try:
            repo = EntityRepository(db)
            event = ActivityEvent(
                entity_id=uuid.UUID(str(project_id)),
                event_type=event_type,
                occurred_at=datetime.now(timezone.utc),
                payload=payload,
            )
            await repo.add_activity(event)
            await repo.increment_engagement(uuid.UUID(str(project_id)))
            await db.commit()
            log.debug("rec.engagement.recorded", project_id=str(project_id), event=event_type)
        except Exception as exc:
            await db.rollback()
            log.warning("rec.engagement.record_failed", error=str(exc))


async def _consume_loop() -> None:
    global _consumer

    _consumer = AIOKafkaConsumer(
        KafkaTopics.ORG_EVENTS,
        KafkaTopics.FEEDBACK_EVENTS,
        KafkaTopics.STAKEHOLDER_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="recommendation_service_group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
    )

    for attempt in range(1, 11):
        try:
            await _consumer.start()
            log.info("rec.consumer.started", topics=[
                KafkaTopics.ORG_EVENTS, KafkaTopics.FEEDBACK_EVENTS, KafkaTopics.STAKEHOLDER_EVENTS,
            ])
            break
        except KafkaConnectionError as exc:
            wait = attempt * 3
            log.warning("rec.consumer.retry", attempt=attempt, wait_s=wait, error=str(exc))
            await asyncio.sleep(wait)
    else:
        log.error("rec.consumer.connect_failed")
        return

    try:
        async for msg in _consumer:
            try:
                event = msg.value
                event_type = event.get("event_type", "")
                payload = event.get("payload", {})

                if event_type in _PROJECT_UPSERT:
                    await _handle_project_upsert(payload, event_type)
                elif event_type in _PROJECT_DEACTIVATE:
                    await _handle_project_deactivate(payload, event_type)
                elif event_type in _FEEDBACK_EVENTS:
                    await _handle_feedback_event(payload, event_type)
                elif event_type in _ENGAGEMENT_EVENTS:
                    await _handle_engagement_event(payload, event_type)
                else:
                    log.debug("rec.consumer.ignored", event_type=event_type)
            except Exception as exc:
                log.error("rec.consumer.message_error", error=str(exc), offset=msg.offset)
    finally:
        await _consumer.stop()
        log.info("rec.consumer.stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    log.info("rec.consumer.task_started")


async def stop_consumer() -> None:
    global _consumer, _consumer_task
    if _consumer:
        await _consumer.stop()
        _consumer = None
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
    log.info("rec.consumer.task_stopped")
