# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  events/producer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/producer.py — Async Kafka producer singleton for translation_service.

Publishes to: riviwa.translation.events

Events published:
  language.preference_set          — user explicitly changed their language
  language.preference_auto_updated — system auto-updated from detection
  language.detected                — detection ran (analytics)
  translation.completed            — provider translation served (cost tracking)

Usage in services:
    from events.producer import get_producer

    producer = await get_producer()
    await producer.language_preference_set(
        user_id           = str(user.id),
        previous_language = "en",
        new_language      = "sw",
        source            = "user_settings",
    )
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import KafkaTopics, TranslationEvents

log = structlog.get_logger(__name__)

_producer: Optional["TranslationProducer"] = None
_producer_lock = asyncio.Lock()


class TranslationProducer:

    def __init__(self) -> None:
        self._p: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._p = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            compression_type="zstd",
            linger_ms=5,
            request_timeout_ms=15_000,
        )
        await self._p.start()
        log.info("translation.producer.started")

    async def stop(self) -> None:
        if self._p:
            await self._p.stop()
            self._p = None
            log.info("translation.producer.stopped")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _envelope(self, event_type: str, payload: dict) -> dict:
        return {
            "event_type":     event_type,
            "event_id":       str(uuid.uuid4()),
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service":        settings.SERVICE_NAME,
            "payload":        payload,
        }

    async def _publish(
        self,
        event_type: str,
        payload:    dict,
        key:        Optional[str] = None,
    ) -> None:
        if not self._p:
            log.warning("translation.producer.not_started", event_type=event_type)
            return
        try:
            await self._p.send_and_wait(
                KafkaTopics.TRANSLATION_EVENTS,
                value=self._envelope(event_type, payload),
                key=key,
            )
            log.debug("translation.event.published", event_type=event_type, key=key)
        except Exception as exc:
            # Never crash the request — event publishing is best-effort
            log.error("translation.producer.publish_failed",
                      event_type=event_type, error=str(exc))

    # ── Public typed event methods ────────────────────────────────────────────

    async def language_preference_set(
        self,
        user_id:           str,
        new_language:      str,
        previous_language: Optional[str] = None,
        fallback_language: Optional[str] = None,
        source:            str           = "user_settings",
        channel:           Optional[str] = None,
    ) -> None:
        """
        Fired when a user explicitly selects a language.

        Triggered by:
          · POST /preferences/{user_id}         — explicit choice in app settings
          · POST /preferences/{user_id}/device-locale  — mobile app sends OS locale
        """
        await self._publish(
            TranslationEvents.PREFERENCE_SET,
            {
                "user_id":           user_id,
                "previous_language": previous_language,
                "new_language":      new_language,
                "fallback_language": fallback_language or settings.FALLBACK_LANGUAGE,
                "source":            source,
                "channel":           channel,
            },
            key=user_id,
        )
        log.info(
            "language.preference_set",
            user_id=user_id,
            previous=previous_language,
            new=new_language,
            source=source,
        )

    async def language_preference_auto_updated(
        self,
        user_id:           str,
        new_language:      str,
        previous_language: Optional[str] = None,
        confidence:        float         = 0.0,
        source:            str           = "text_detection",
        channel:           Optional[str] = None,
        session_id:        Optional[str] = None,
    ) -> None:
        """
        Fired when the system automatically updates the user's language based
        on detection (e.g. user writes in Swahili → language auto-set to 'sw').

        Triggered by:
          · POST /detect                   when update_preference=true
          · POST /detect/channel           when update_preference=true
          · POST /internal/detect-and-update
        """
        await self._publish(
            TranslationEvents.PREFERENCE_AUTO_UPDATED,
            {
                "user_id":           user_id,
                "previous_language": previous_language,
                "new_language":      new_language,
                "confidence":        round(confidence, 4),
                "source":            source,
                "channel":           channel,
                "session_id":        session_id,
            },
            key=user_id,
        )
        log.info(
            "language.preference_auto_updated",
            user_id=user_id,
            previous=previous_language,
            new=new_language,
            confidence=confidence,
            source=source,
        )

    async def language_detected(
        self,
        detected_language:  str,
        confidence:         float,
        source:             str,
        preference_updated: bool,
        user_id:            Optional[str] = None,
        channel:            Optional[str] = None,
        session_id:         Optional[str] = None,
    ) -> None:
        """
        Fired on every detection call regardless of whether the preference changed.
        Feeds the admin dashboard language distribution analytics.

        Triggered by:
          · POST /detect
          · POST /detect/channel
          · POST /internal/detect-and-update
        """
        await self._publish(
            TranslationEvents.DETECTED,
            {
                "user_id":            user_id,
                "detected_language":  detected_language,
                "confidence":         round(confidence, 4),
                "source":             source,
                "channel":            channel,
                "session_id":         session_id,
                "preference_updated": preference_updated,
            },
            key=user_id,
        )

    async def translation_completed(
        self,
        source_language: str,
        target_language: str,
        provider:        str,
        char_count:      int,
    ) -> None:
        """
        Fired after every non-cached translation (actual provider call).
        Used for usage analytics and provider cost tracking.

        Triggered by:
          · POST /translate        (cache miss)
          · POST /translate/batch  (for each uncached string)
        """
        await self._publish(
            TranslationEvents.TRANSLATION_COMPLETED,
            {
                "source_language": source_language,
                "target_language": target_language,
                "provider":        provider,
                "cached":          False,
                "char_count":      char_count,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Singleton helpers — used by main.py lifespan and service layer
# ─────────────────────────────────────────────────────────────────────────────

async def get_producer() -> TranslationProducer:
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            _producer = TranslationProducer()
            await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
