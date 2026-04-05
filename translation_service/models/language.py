# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  models/language.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/language.py
═══════════════════════════════════════════════════════════════════════════════
SQLModel table definitions for the translation_service.

TABLES
──────────────────────────────────────────────────────────────────────────────
  supported_languages      — master list of BCP-47 language codes the platform
                             supports (seeded at startup, managed by admins)

  user_language_prefs      — one row per user: preferred language, device locale,
                             per-channel detected languages, fallback settings

  language_detection_logs  — audit trail of every auto-detection event across
                             all channels (SMS, WhatsApp, call, web, mobile)

DESIGN PRINCIPLES
──────────────────────────────────────────────────────────────────────────────
  · user_id is a bare UUID — translation_service does NOT import user models
    from auth_service. Cross-service references are by ID only.

  · detected_languages JSONB stores a map of channel → [language codes] so
    the service remembers which language a user tends to use per channel:
      {"sms": ["sw", "en"], "whatsapp": ["sw"], "web": ["en"]}

  · SupportedLanguage is the single source of truth for what codes are valid.
    All foreign key-like references (preferred_language etc.) are validated
    against this table at the service layer, not enforced by DB FK so that
    the table can be hot-updated without cascade concerns.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class ChannelSource(str, Enum):
    """Channel that triggered a language detection event."""
    SMS       = "sms"
    WHATSAPP  = "whatsapp"
    CALL      = "call"
    WEB       = "web"
    MOBILE    = "mobile"
    IVR       = "ivr"       # Interactive Voice Response (USSD/call)


class DetectionSource(str, Enum):
    """How the language was determined."""
    DEVICE_LOCALE  = "device_locale"   # OS/browser locale sent by client
    TEXT_DETECTION = "text_detection"  # langdetect on message content
    USER_SET       = "user_set"        # user explicitly chose in settings


# ─────────────────────────────────────────────────────────────────────────────
# supported_languages
# ─────────────────────────────────────────────────────────────────────────────

class SupportedLanguage(SQLModel, table=True):
    """
    Master list of BCP-47 language codes the platform can serve.

    Seeded at startup (see db/init_db.py).
    Platform admins can add/deactivate via PATCH /languages/{code}.

    Examples:
      code="sw"  name="Swahili"  native_name="Kiswahili"  is_rtl=False
      code="ar"  name="Arabic"   native_name="العربية"    is_rtl=True
    """
    __tablename__ = "supported_languages"

    code: str = Field(
        primary_key=True,
        max_length=10,
        description="BCP-47 language tag, e.g. 'sw', 'en', 'fr', 'ar'",
    )
    name:        str  = Field(max_length=80,  nullable=False, description="English name")
    native_name: str  = Field(max_length=80,  nullable=False, description="Name in that language")
    flag_emoji:  Optional[str] = Field(default=None, max_length=10)
    is_rtl:      bool = Field(default=False,  description="Right-to-left script")
    is_active:   bool = Field(default=True,   index=True)

    # Translation provider support flags
    google_supported: bool = Field(default=True)
    deepl_supported:  bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


# ─────────────────────────────────────────────────────────────────────────────
# user_language_prefs
# ─────────────────────────────────────────────────────────────────────────────

class UserLanguagePreference(SQLModel, table=True):
    """
    One row per platform user capturing their full language context.

    preferred_language:  The canonical language used for all rendered content
                         (notifications, feedback templates, UI).

    device_locale:       Raw BCP-47 locale string sent by the mobile app or
                         browser, e.g. "sw-TZ", "en-GB". Stored for audit;
                         the service normalises it to a supported code.

    detected_languages:  JSONB map of channel → ordered list of detected codes.
                         Most-recently-detected first per channel.
                         {"sms": ["sw", "en"], "whatsapp": ["sw"]}

    fallback_language:   Used when preferred_language content is unavailable.
                         Defaults to platform DEFAULT_LANGUAGE setting.

    auto_detect_enabled: When True the service updates preferred_language
                         automatically when detection confidence is high.
    """
    __tablename__ = "user_language_prefs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(nullable=False, index=True, unique=True)

    # ── Language settings ─────────────────────────────────────────────────────
    preferred_language: str  = Field(
        max_length=10,
        nullable=False,
        default="sw",
        description="BCP-47 code. Must exist in supported_languages.",
    )
    fallback_language: str   = Field(
        max_length=10,
        nullable=False,
        default="en",
    )
    device_locale: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Raw device locale e.g. 'sw-TZ', 'en-GB'. Set by mobile SDK.",
    )
    detected_languages: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Per-channel detected language history. {channel: [codes]}",
    )

    # ── Behaviour flags ───────────────────────────────────────────────────────
    auto_detect_enabled: bool = Field(
        default=True,
        description="Automatically update preferred_language on high-confidence detection.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.utcnow(),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# language_detection_logs
# ─────────────────────────────────────────────────────────────────────────────

class LanguageDetectionLog(SQLModel, table=True):
    """
    Append-only audit trail for every language detection / set event.

    Captures:
      · Which channel triggered the detection
      · Confidence score from the detection library
      · Whether the user's preference was updated as a result
      · First 200 chars of input text (for quality monitoring / debugging)

    user_id is nullable to support anonymous channel sessions (e.g. an
    SMS from an unregistered phone number).
    """
    __tablename__ = "language_detection_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    user_id:    Optional[uuid.UUID] = Field(default=None, nullable=True,  index=True)
    session_id: Optional[str]       = Field(default=None, max_length=100, index=True,
                                            description="Channel session ID (if applicable)")

    channel: ChannelSource = Field(
        sa_column=Column(
            SAEnum(ChannelSource, name="channel_source"),
            nullable=False,
            index=True,
        )
    )
    detection_source: DetectionSource = Field(
        sa_column=Column(
            SAEnum(DetectionSource, name="detection_source"),
            nullable=False,
        )
    )

    detected_language: str   = Field(max_length=10, nullable=False, index=True)
    confidence:        float = Field(nullable=False, description="0.0–1.0 confidence score")
    text_sample:       Optional[str] = Field(
        default=None,
        max_length=200,
        description="First 200 chars of the input text, stored for quality audit.",
    )
    preference_updated: bool = Field(
        default=False,
        description="True if this detection caused UserLanguagePreference.preferred_language to change.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
