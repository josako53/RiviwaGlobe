# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  repositories/language_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""repositories/language_repository.py — pure DB access layer."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.language import (
    ChannelSource,
    DetectionSource,
    LanguageDetectionLog,
    SupportedLanguage,
    UserLanguagePreference,
)

log = structlog.get_logger(__name__)


class LanguageRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── SupportedLanguage ─────────────────────────────────────────────────────

    async def get_language(self, code: str) -> Optional[SupportedLanguage]:
        result = await self.db.execute(
            select(SupportedLanguage).where(SupportedLanguage.code == code)
        )
        return result.scalar_one_or_none()

    async def list_languages(
        self,
        active_only: bool = True,
    ) -> tuple[list[SupportedLanguage], int]:
        q = select(SupportedLanguage)
        if active_only:
            q = q.where(SupportedLanguage.is_active == True)  # noqa: E712
        q = q.order_by(SupportedLanguage.name.asc())
        rows  = (await self.db.execute(q)).scalars().all()
        total = len(rows)
        return list(rows), total

    async def language_exists(self, code: str) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(SupportedLanguage)
            .where(SupportedLanguage.code == code, SupportedLanguage.is_active == True)  # noqa: E712
        )
        return (result.scalar_one() or 0) > 0

    async def create_language(
        self,
        code: str,
        name: str,
        native_name: str,
        *,
        flag_emoji:       Optional[str] = None,
        is_rtl:           bool          = False,
        google_supported: bool          = True,
        deepl_supported:  bool          = False,
    ) -> SupportedLanguage:
        lang = SupportedLanguage(
            code=code, name=name, native_name=native_name,
            flag_emoji=flag_emoji, is_rtl=is_rtl,
            google_supported=google_supported, deepl_supported=deepl_supported,
        )
        self.db.add(lang)
        await self.db.flush()
        return lang

    async def set_language_active(self, code: str, is_active: bool) -> Optional[SupportedLanguage]:
        lang = await self.get_language(code)
        if not lang:
            return None
        lang.is_active = is_active
        self.db.add(lang)
        await self.db.flush()
        return lang

    # ── UserLanguagePreference ────────────────────────────────────────────────

    async def get_preference(self, user_id: uuid.UUID) -> Optional[UserLanguagePreference]:
        result = await self.db.execute(
            select(UserLanguagePreference)
            .where(UserLanguagePreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_preference(
        self,
        user_id:             uuid.UUID,
        preferred_language:  str,
        fallback_language:   str               = "en",
        device_locale:       Optional[str]     = None,
        auto_detect_enabled: bool              = True,
    ) -> UserLanguagePreference:
        pref = await self.get_preference(user_id)
        if pref:
            pref.preferred_language  = preferred_language
            pref.fallback_language   = fallback_language
            pref.auto_detect_enabled = auto_detect_enabled
            if device_locale is not None:
                pref.device_locale = device_locale
        else:
            pref = UserLanguagePreference(
                user_id=user_id,
                preferred_language=preferred_language,
                fallback_language=fallback_language,
                device_locale=device_locale,
                auto_detect_enabled=auto_detect_enabled,
            )
        self.db.add(pref)
        await self.db.flush()
        return pref

    async def set_device_locale(
        self,
        user_id:       uuid.UUID,
        device_locale: str,
        normalised_code: str,
        override_existing: bool = False,
    ) -> UserLanguagePreference:
        """
        Update device_locale. If override_existing=True or no preference exists,
        also updates preferred_language to the normalised code.
        """
        pref = await self.get_preference(user_id)
        if pref:
            pref.device_locale = device_locale
            if override_existing:
                pref.preferred_language = normalised_code
        else:
            pref = UserLanguagePreference(
                user_id=user_id,
                preferred_language=normalised_code,
                device_locale=device_locale,
            )
        self.db.add(pref)
        await self.db.flush()
        return pref

    async def update_preferred_language(
        self,
        user_id:            uuid.UUID,
        preferred_language: str,
    ) -> Optional[UserLanguagePreference]:
        pref = await self.get_preference(user_id)
        if not pref:
            return None
        pref.preferred_language = preferred_language
        pref.updated_at = datetime.now(timezone.utc)
        self.db.add(pref)
        await self.db.flush()
        return pref

    async def append_detected_language(
        self,
        user_id:  uuid.UUID,
        channel:  str,
        lang_code: str,
    ) -> None:
        """
        Append lang_code to detected_languages[channel] list (max 5 kept per channel).
        Creates the preference record if it doesn't exist.
        """
        pref = await self.get_preference(user_id)
        if not pref:
            pref = UserLanguagePreference(
                user_id=user_id,
                preferred_language=lang_code,
            )
        detected = pref.detected_languages or {}
        channel_list: list = detected.get(channel, [])
        if lang_code in channel_list:
            channel_list.remove(lang_code)
        channel_list.insert(0, lang_code)
        detected[channel] = channel_list[:5]   # keep latest 5 per channel
        pref.detected_languages = detected
        pref.updated_at = datetime.now(timezone.utc)
        self.db.add(pref)
        await self.db.flush()

    # ── LanguageDetectionLog ──────────────────────────────────────────────────

    async def log_detection(
        self,
        channel:            ChannelSource,
        detection_source:   DetectionSource,
        detected_language:  str,
        confidence:         float,
        *,
        user_id:            Optional[uuid.UUID] = None,
        session_id:         Optional[str]       = None,
        text_sample:        Optional[str]       = None,
        preference_updated: bool                = False,
    ) -> LanguageDetectionLog:
        entry = LanguageDetectionLog(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
            detection_source=detection_source,
            detected_language=detected_language,
            confidence=confidence,
            text_sample=text_sample[:200] if text_sample else None,
            preference_updated=preference_updated,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_detection_logs(
        self,
        user_id: uuid.UUID,
        limit:   int = 50,
        skip:    int = 0,
    ) -> tuple[list[LanguageDetectionLog], int]:
        base = (
            select(LanguageDetectionLog)
            .where(LanguageDetectionLog.user_id == user_id)
            .order_by(LanguageDetectionLog.created_at.desc())
        )
        count_q = select(func.count()).select_from(base.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()
        rows    = (await self.db.execute(base.offset(skip).limit(limit))).scalars().all()
        return list(rows), total

    async def delete_preference(self, user_id: uuid.UUID) -> bool:
        """
        GDPR: hard-delete the user's language preference row.
        Called when user is deactivated or banned.
        Returns True if a row was deleted, False if none existed.
        """
        from sqlalchemy import delete as sa_delete
        result = await self.db.execute(
            sa_delete(UserLanguagePreference).where(
                UserLanguagePreference.user_id == user_id
            )
        )
        await self.db.flush()
        return result.rowcount > 0

