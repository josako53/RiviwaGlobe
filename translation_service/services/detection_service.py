# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  services/detection_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/detection_service.py — Language detection orchestration.

Uses langdetect under the hood. Handles:
  · Single text detection
  · Channel session detection (combines multiple messages for higher accuracy)
  · Device locale normalisation (sw-TZ → sw)
  · Logging and optional preference updates
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog

from core.config import settings
from core.exceptions import DetectionFailedError
from events.producer import get_producer
from models.language import ChannelSource, DetectionSource
from repositories.language_repository import LanguageRepository

log = structlog.get_logger(__name__)

# BCP-47 primary subtag normalisation (strip region: "sw-TZ" → "sw")
def _normalise_locale(locale: str) -> str:
    """Strip region subtag: 'sw-TZ' → 'sw', 'en_GB' → 'en'."""
    return locale.replace("_", "-").split("-")[0].lower()


class DetectionService:

    def __init__(self, repo: LanguageRepository) -> None:
        self.repo = repo

    # ── Core detection ────────────────────────────────────────────────────────

    def _run_langdetect(self, text: str) -> tuple[str, float, list[dict]]:
        """
        Run langdetect on text.
        Returns (best_lang_code, confidence, alternatives).
        Raises DetectionFailedError if detection fails.
        """
        if len(text.strip()) < settings.MIN_DETECT_CHARS:
            raise DetectionFailedError(
                f"Text too short for reliable detection (minimum {settings.MIN_DETECT_CHARS} chars)."
            )
        try:
            from langdetect import detect_langs  # type: ignore
            results    = detect_langs(text)
            best       = results[0]
            alternatives = [
                {"language": str(r.lang), "confidence": round(r.prob, 4)}
                for r in results[1:5]
            ]
            return str(best.lang), round(best.prob, 4), alternatives
        except Exception as exc:
            log.warning("detection.langdetect_failed", error=str(exc))
            raise DetectionFailedError(f"Language detection failed: {exc}")

    async def detect_text(
        self,
        text:              str,
        *,
        user_id:           Optional[uuid.UUID] = None,
        channel:           Optional[str]       = None,
        session_id:        Optional[str]       = None,
        update_preference: bool                = False,
    ) -> dict:
        """
        Detect language from a single text string.
        Returns a dict matching DetectLanguageResponse schema.
        """
        lang_code, confidence, alternatives = self._run_langdetect(text)
        is_supported  = await self.repo.language_exists(lang_code)
        pref_updated  = False

        ch_source = (
            ChannelSource(channel)
            if channel and channel in [c.value for c in ChannelSource]
            else ChannelSource.WEB
        )

        if user_id:
            # Log the detection
            should_update = (
                update_preference
                and is_supported
                and confidence >= settings.MIN_DETECTION_CONFIDENCE
            )
            if should_update:
                pref = await self.repo.get_preference(user_id)
                if pref and pref.auto_detect_enabled:
                    await self.repo.update_preferred_language(user_id, lang_code)
                    pref_updated = True

            if channel:
                await self.repo.append_detected_language(user_id, ch_source.value, lang_code)

            await self.repo.log_detection(
                channel=ch_source,
                detection_source=DetectionSource.TEXT_DETECTION,
                detected_language=lang_code,
                confidence=confidence,
                user_id=user_id,
                session_id=session_id,
                text_sample=text[:200],
                preference_updated=pref_updated,
            )

        # Publish events (best-effort — never blocks the response)
        try:
            producer = await get_producer()

            # language.detected — fires on every detection (analytics)
            await producer.language_detected(
                detected_language  = lang_code,
                confidence         = confidence,
                source             = "text_detection",
                preference_updated = pref_updated,
                user_id            = str(user_id) if user_id else None,
                channel            = channel,
                session_id         = session_id,
            )

            # language.preference_auto_updated — only if preference actually changed
            if pref_updated and user_id:
                await producer.language_preference_auto_updated(
                    user_id    = str(user_id),
                    new_language  = lang_code,
                    confidence    = confidence,
                    source        = "text_detection",
                    channel       = channel,
                    session_id    = session_id,
                )
        except Exception as _exc:
            log.warning("detection.event_publish_failed", error=str(_exc))

        return {
            "detected_language": lang_code,
            "confidence":        confidence,
            "is_supported":      is_supported,
            "alternatives":      alternatives,
            "preference_updated": pref_updated,
        }

    async def detect_channel_session(
        self,
        messages:          list[str],
        channel:           str,
        *,
        user_id:           Optional[uuid.UUID] = None,
        session_id:        Optional[str]       = None,
        update_preference: bool                = True,
    ) -> dict:
        """
        Detect language from a full channel session (all messages combined).
        Concatenating messages gives langdetect more context → higher accuracy.
        """
        combined = " ".join(m.strip() for m in messages if m.strip())
        return await self.detect_text(
            combined,
            user_id=user_id,
            channel=channel,
            session_id=session_id,
            update_preference=update_preference,
        )

    # ── Device locale normalisation ───────────────────────────────────────────

    async def set_device_locale(
        self,
        user_id:           uuid.UUID,
        device_locale:     str,
        override_existing: bool = False,
    ) -> dict:
        """
        Called by mobile app on startup with the OS locale (e.g. 'sw-TZ').
        Normalises to a supported language code, updates the preference row,
        and logs a DEVICE_LOCALE detection event.
        Returns a dict matching UserLanguagePrefResponse.
        """
        normalised = _normalise_locale(device_locale)
        is_supported = await self.repo.language_exists(normalised)

        # Fall back to platform default if device locale not supported
        if not is_supported:
            log.info(
                "detection.device_locale_unsupported",
                raw=device_locale,
                normalised=normalised,
                fallback=settings.DEFAULT_LANGUAGE,
            )
            normalised = settings.DEFAULT_LANGUAGE

        pref = await self.repo.set_device_locale(
            user_id=user_id,
            device_locale=device_locale,
            normalised_code=normalised,
            override_existing=override_existing,
        )

        await self.repo.log_detection(
            channel=ChannelSource.MOBILE,
            detection_source=DetectionSource.DEVICE_LOCALE,
            detected_language=normalised,
            confidence=1.0,   # device locale is deterministic
            user_id=user_id,
            text_sample=device_locale,
            preference_updated=override_existing or pref.preferred_language == normalised,
        )

        return pref
