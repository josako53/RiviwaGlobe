# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  services/preference_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/preference_service.py — User language preference management.

Handles:
  · Explicit language selection (user picks from settings UI)
  · Device locale sync (mobile SDK sends OS locale on app start)
  · Preference retrieval for content rendering by other services
  · Fallback resolution when no preference exists
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog

from core.config import settings
from core.exceptions import LanguageNotSupportedError, LanguagePreferenceNotFoundError
from events.producer import get_producer
from models.language import ChannelSource, DetectionSource
from repositories.language_repository import LanguageRepository

log = structlog.get_logger(__name__)

# Normalise device locale: "sw-TZ" → "sw", "en_GB" → "en"
def _normalise_locale(locale: str) -> str:
    return locale.replace("_", "-").split("-")[0].lower().strip()


class PreferenceService:

    def __init__(self, repo: LanguageRepository) -> None:
        self.repo = repo

    # ── Get preference ────────────────────────────────────────────────────────

    async def get_preference(self, user_id: uuid.UUID) -> dict:
        """
        Return language preference for a user.
        Creates a default row (sw → en) on first access so every user
        always has a preference record.
        """
        pref = await self.repo.get_preference(user_id)
        if pref is None:
            # Auto-create with platform defaults
            pref = await self.repo.upsert_preference(
                user_id=user_id,
                preferred_language=settings.DEFAULT_LANGUAGE,
                fallback_language=settings.FALLBACK_LANGUAGE,
            )
            await self.repo.db.commit()
            log.info("preference.auto_created", user_id=str(user_id),
                     preferred=settings.DEFAULT_LANGUAGE)
        return pref

    async def get_language_for_user(self, user_id: uuid.UUID) -> dict:
        """
        Minimal language info for internal callers (notification_service,
        feedback_service etc.). Returns preferred + fallback codes only.
        """
        pref = await self.get_preference(user_id)
        return {
            "user_id":            user_id,
            "preferred_language": pref.preferred_language,
            "fallback_language":  pref.fallback_language,
            "has_preference":     True,
        }

    # ── Set preference explicitly ─────────────────────────────────────────────

    async def set_preference(
        self,
        user_id:             uuid.UUID,
        preferred_language:  str,
        *,
        fallback_language:   Optional[str] = None,
        auto_detect_enabled: Optional[bool] = None,
    ) -> object:
        """
        Called when a user explicitly selects a language in the settings UI
        (web or mobile). Validates the language code first.
        """
        # Validate target language exists in supported_languages
        if not await self.repo.language_exists(preferred_language):
            raise LanguageNotSupportedError(
                f"Language '{preferred_language}' is not supported. "
                "Call GET /api/v1/languages to see available codes."
            )
        if fallback_language and not await self.repo.language_exists(fallback_language):
            raise LanguageNotSupportedError(
                f"Fallback language '{fallback_language}' is not supported."
            )

        updates: dict = {"preferred_language": preferred_language}
        if fallback_language is not None:
            updates["fallback_language"] = fallback_language
        if auto_detect_enabled is not None:
            updates["auto_detect_enabled"] = auto_detect_enabled

        pref = await self.repo.upsert_preference(user_id=user_id, **updates)
        await self.repo.db.commit()

        # Log the explicit set event
        await self.repo.log_detection(
            channel=ChannelSource.WEB,
            detection_source=DetectionSource.USER_SET,
            detected_language=preferred_language,
            confidence=1.0,
            user_id=user_id,
            preference_updated=True,
        )
        await self.repo.db.commit()

        log.info("preference.explicitly_set",
                 user_id=str(user_id), language=preferred_language)

        # Publish language.preference_set event
        try:
            producer = await get_producer()
            await producer.language_preference_set(
                user_id           = str(user_id),
                new_language      = preferred_language,
                previous_language = None,   # repo upsert handles history
                fallback_language = fallback_language or settings.FALLBACK_LANGUAGE,
                source            = "user_settings",
            )
        except Exception as _exc:
            log.warning("preference.event_publish_failed", error=str(_exc))

        return pref

    # ── Device locale sync ────────────────────────────────────────────────────

    async def sync_device_locale(
        self,
        user_id:           uuid.UUID,
        device_locale:     str,
        override_existing: bool = False,
    ) -> object:
        """
        Called by the mobile SDK on app startup.
        Normalises the OS locale (e.g. 'sw-TZ') to a supported BCP-47 code.

        override_existing=False (default):
          Only updates preferred_language if the user has no explicit preference yet
          (i.e. they're on the platform default). Respects a user who already
          chose English not having it switched to Swahili just because they
          picked up a Tanzanian SIM.

        override_existing=True:
          Always sync — useful for onboarding flow where the app wants to
          pre-fill the device language.
        """
        normalised = _normalise_locale(device_locale)

        # If the normalised code isn't supported, fall back to platform default
        if not await self.repo.language_exists(normalised):
            log.info(
                "preference.device_locale_unsupported",
                raw=device_locale, normalised=normalised,
                using=settings.DEFAULT_LANGUAGE,
            )
            normalised = settings.DEFAULT_LANGUAGE

        pref = await self.repo.set_device_locale(
            user_id=user_id,
            device_locale=device_locale,
            normalised_code=normalised,
            override_existing=override_existing,
        )
        await self.repo.db.commit()

        await self.repo.log_detection(
            channel=ChannelSource.MOBILE,
            detection_source=DetectionSource.DEVICE_LOCALE,
            detected_language=normalised,
            confidence=1.0,
            user_id=user_id,
            text_sample=device_locale,
            preference_updated=override_existing or pref.preferred_language == normalised,
        )
        await self.repo.db.commit()

        log.info("preference.device_locale_synced",
                 user_id=str(user_id), raw=device_locale, normalised=normalised)
        return pref
