# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  events/consumer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/consumer.py — Kafka consumer for riviwa_auth_service.

CONSUMES: riviwa.translation.events  (published by translation_service)

  language.preference_set
  ──────────────────────────────────────────────────────────────────────────
  User explicitly chose a language in app settings or mobile SDK sent the
  device locale. Update User.language to keep the sync copy current.

  language.preference_auto_updated
  ──────────────────────────────────────────────────────────────────────────
  System auto-detected the user's language from their submitted text with
  high confidence and updated their preference. Mirror to User.language.

  All other translation events (language.detected, translation.completed)
  are ignored — they are analytics events, not state change events.

Consumer group: auth_service_translation_events
  Separate from all other consumer groups so auth_service gets its own
  copy of every event regardless of what other services consume.

Why Option C (sync copy) vs Option B (HTTP pull):
  · User.language on the JWT means downstream services can read the
    language from the token claims WITHOUT making an extra HTTP call to
    translation_service on every request.
  · The sync is eventual — there is a brief window between a preference
    change and the next token refresh where the JWT may carry a stale
    language code. This is acceptable (language changes are rare).
  · translation_service remains the authoritative source; User.language
    is a convenience cache only.
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
from events.topics import KafkaTopics
from repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)

_consumer: Optional[AIOKafkaConsumer] = None
_consumer_task: Optional[asyncio.Task] = None

# Translation event types we care about
_LANGUAGE_CHANGE_EVENTS = frozenset({
    "language.preference_set",
    "language.preference_auto_updated",
})


# ─────────────────────────────────────────────────────────────────────────────
# Event handler
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_language_changed(payload: dict, event_type: str) -> None:
    """
    Mirror the language change to User.language in auth_db.

    Payload fields (both events share this shape):
      user_id      — UUID of the user whose language changed
      new_language — BCP-47 code of the new preferred language
    """
    raw_user_id  = payload.get("user_id")
    new_language = payload.get("new_language")

    if not raw_user_id or not new_language:
        log.warning(
            "auth.consumer.language_changed.missing_fields",
            event_type=event_type,
            payload_keys=list(payload.keys()),
        )
        return

    try:
        user_id = uuid.UUID(str(raw_user_id))
    except ValueError:
        log.warning("auth.consumer.language_changed.invalid_uuid",
                    raw=raw_user_id)
        return

    async with AsyncSessionLocal() as db:
        try:
            repo = UserRepository(db)
            await repo.update_language(user_id, new_language)
            await db.commit()

            log.info(
                "auth.user.language_synced",
                user_id=str(user_id),
                language=new_language,
                source=event_type,
            )
        except Exception as exc:
            await db.rollback()
            log.error(
                "auth.consumer.language_sync_failed",
                user_id=str(user_id),
                language=new_language,
                error=str(exc),
            )


# ─────────────────────────────────────────────────────────────────────────────
# Main consume loop
# ─────────────────────────────────────────────────────────────────────────────

async def _consume_loop() -> None:
    global _consumer

    _consumer = AIOKafkaConsumer(
        KafkaTopics.TRANSLATION_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="auth_service_translation_events",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
    )

    # Retry with backoff — Kafka may not be ready at startup
    for attempt in range(1, 11):
        try:
            await _consumer.start()
            log.info(
                "auth.consumer.started",
                topic=KafkaTopics.TRANSLATION_EVENTS,
                group="auth_service_translation_events",
            )
            break
        except KafkaConnectionError as exc:
            wait = attempt * 3
            log.warning(
                "auth.consumer.connect_retry",
                attempt=attempt,
                wait_s=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)
    else:
        log.error("auth.consumer.connect_failed",
                  topic=KafkaTopics.TRANSLATION_EVENTS)
        return

    try:
        async for msg in _consumer:
            try:
                event      = msg.value
                event_type = event.get("event_type", "")
                payload    = event.get("payload", {})

                if event_type in _LANGUAGE_CHANGE_EVENTS:
                    await _handle_language_changed(payload, event_type)
                else:
                    # language.detected, translation.completed → analytics only
                    log.debug("auth.consumer.ignored", event_type=event_type)

            except Exception as exc:
                log.error(
                    "auth.consumer.message_error",
                    error=str(exc),
                    offset=msg.offset,
                    partition=msg.partition,
                )
                # Never crash on a bad message — skip and continue
    finally:
        await _consumer.stop()
        log.info("auth.consumer.stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle helpers — called from main.py lifespan
# ─────────────────────────────────────────────────────────────────────────────

async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    log.info("auth.consumer.task_started",
             topic=KafkaTopics.TRANSLATION_EVENTS)


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
    log.info("auth.consumer.task_stopped")
