# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  events/consumer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/consumer.py — Kafka consumer for translation_service.

CONSUMES: riviwa.user.events  (published by riviwa_auth_service)

  user.registered
  ──────────────────────────────────────────────────────────────────────────
  Auto-creates a default language preference row (sw → en) for every new
  user. This means every user always has a preference record from day one —
  no "preference not found" cases in detection or rendering.

  user.deactivated | user.banned
  ──────────────────────────────────────────────────────────────────────────
  Soft-deletes (nulls out) the user's preference data for GDPR compliance.
  Does NOT hard-delete — audit trail is preserved in detection_logs.
  The preference row itself is removed so the user's language choice is
  no longer accessible.

Consumer group: translation_service_user_events
  Separate consumer group from feedback/stakeholder ensures each service
  gets its own copy of every event (Kafka fan-out pattern).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import KafkaTopics, UserEvents
from repositories.language_repository import LanguageRepository

log = structlog.get_logger(__name__)

_consumer: Optional[AIOKafkaConsumer] = None
_consumer_task: Optional[asyncio.Task] = None


# ─────────────────────────────────────────────────────────────────────────────
# Event handlers
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_user_registered(payload: dict) -> None:
    """
    Create a default language preference row for the new user.
    Default: preferred=sw (Kiswahili), fallback=en (English).
    Matches Tanzania context — users can change it later.
    """
    raw_user_id = payload.get("user_id") or payload.get("id")
    if not raw_user_id:
        log.warning("consumer.user_registered.missing_user_id", payload=payload)
        return

    try:
        user_id = uuid.UUID(str(raw_user_id))
    except ValueError:
        log.warning("consumer.user_registered.invalid_uuid", raw=raw_user_id)
        return

    async with AsyncSessionLocal() as db:
        try:
            repo = LanguageRepository(db)

            # Check if preference already exists (idempotent)
            existing = await repo.get_preference(user_id)
            if existing:
                log.debug("consumer.user_registered.preference_exists",
                          user_id=str(user_id))
                return

            # Create default preference
            await repo.upsert_preference(
                user_id=user_id,
                preferred_language=settings.DEFAULT_LANGUAGE,
                fallback_language=settings.FALLBACK_LANGUAGE,
            )
            await db.commit()

            log.info(
                "consumer.user_registered.preference_created",
                user_id=str(user_id),
                preferred=settings.DEFAULT_LANGUAGE,
                fallback=settings.FALLBACK_LANGUAGE,
            )
        except Exception as exc:
            await db.rollback()
            log.error("consumer.user_registered.failed",
                      user_id=str(user_id), error=str(exc))


async def _handle_user_deactivated_or_banned(payload: dict, event_type: str) -> None:
    """
    GDPR: remove user's language preference when their account is closed.
    Detection logs retain the user_id for analytics but the preference
    (which contains the user's explicit language choice) is deleted.
    """
    raw_user_id = payload.get("user_id") or payload.get("id")
    if not raw_user_id:
        return

    try:
        user_id = uuid.UUID(str(raw_user_id))
    except ValueError:
        log.warning("consumer.deactivated.invalid_uuid", raw=raw_user_id)
        return

    async with AsyncSessionLocal() as db:
        try:
            repo = LanguageRepository(db)
            deleted = await repo.delete_preference(user_id)
            await db.commit()

            if deleted:
                log.info(
                    "consumer.user_preference_deleted",
                    user_id=str(user_id),
                    reason=event_type,
                )
        except Exception as exc:
            await db.rollback()
            log.error("consumer.deactivation_handler.failed",
                      user_id=str(user_id), error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Main consume loop
# ─────────────────────────────────────────────────────────────────────────────

async def _consume_loop() -> None:
    global _consumer

    _consumer = AIOKafkaConsumer(
        KafkaTopics.USER_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="translation_service_user_events",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
    )

    # Retry connection with backoff — Kafka may not be ready immediately
    for attempt in range(1, 11):
        try:
            await _consumer.start()
            log.info("translation.consumer.started",
                     topic=KafkaTopics.USER_EVENTS)
            break
        except KafkaConnectionError as exc:
            wait = attempt * 3
            log.warning("translation.consumer.connect_retry",
                        attempt=attempt, wait_s=wait, error=str(exc))
            await asyncio.sleep(wait)
    else:
        log.error("translation.consumer.connect_failed",
                  topic=KafkaTopics.USER_EVENTS)
        return

    try:
        async for msg in _consumer:
            try:
                event      = msg.value
                event_type = event.get("event_type", "")
                payload    = event.get("payload", {})

                if event_type == UserEvents.REGISTERED:
                    await _handle_user_registered(payload)

                elif event_type in (UserEvents.DEACTIVATED, UserEvents.BANNED):
                    await _handle_user_deactivated_or_banned(payload, event_type)

                # All other user events (profile_updated etc.) are ignored
                else:
                    log.debug("translation.consumer.ignored",
                              event_type=event_type)

            except Exception as exc:
                log.error("translation.consumer.message_error",
                          error=str(exc),
                          offset=msg.offset,
                          partition=msg.partition)
                # Continue — never crash the consumer on a bad message
    finally:
        await _consumer.stop()
        log.info("translation.consumer.stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle helpers — called from main.py lifespan
# ─────────────────────────────────────────────────────────────────────────────

async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    log.info("translation.consumer.task_started")


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
    log.info("translation.consumer.task_stopped")
