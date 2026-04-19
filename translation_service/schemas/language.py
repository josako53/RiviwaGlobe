# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  schemas/language.py
# ───────────────────────────────────────────────────────────────────────────
"""schemas/language.py — Pydantic v2 schemas for the translation_service."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Supported Languages
# ─────────────────────────────────────────────────────────────────────────────

class LanguageResponse(BaseModel):
    """Public representation of a supported language."""
    model_config = ConfigDict(from_attributes=True)

    code:             str
    name:             str
    native_name:      str
    flag_emoji:       Optional[str] = None
    is_rtl:           bool
    is_active:        bool
    google_supported: bool
    deepl_supported:  bool


class LanguageListResponse(BaseModel):
    items: List[LanguageResponse]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# User Language Preferences
# ─────────────────────────────────────────────────────────────────────────────

class UserLanguagePrefResponse(BaseModel):
    """Full language preference record for a user."""
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    user_id:             uuid.UUID
    preferred_language:  str
    fallback_language:   str
    device_locale:       Optional[str]        = None
    detected_languages:  Optional[Dict]       = None
    auto_detect_enabled: bool
    created_at:          datetime
    updated_at:          datetime


class SetLanguageRequest(BaseModel):
    """
    Body for POST /preferences/{user_id} — explicitly set preferred language.
    Called by web/mobile when user picks a language in settings.
    """
    preferred_language:  str            = Field(
        min_length=2, max_length=10,
        description="BCP-47 language code, e.g. 'sw', 'en', 'fr'",
    )
    fallback_language:   Optional[str]  = Field(
        default=None, min_length=2, max_length=10,
    )
    auto_detect_enabled: Optional[bool] = None


class SetDeviceLocaleRequest(BaseModel):
    """
    Body for POST /preferences/{user_id}/device-locale.
    Called by the mobile SDK on app start — passes the OS locale string.
    The service normalises it (e.g. 'sw-TZ' → 'sw') and updates preferred_language
    if no preference has been explicitly set yet.
    """
    device_locale: str = Field(
        min_length=2, max_length=20,
        description="Raw BCP-47 locale from the device OS, e.g. 'sw-TZ', 'en-GB', 'fr'.",
        examples=["sw-TZ", "en-GB", "fr"],
    )
    override_existing: bool = Field(
        default=False,
        description="If True, overwrite an existing explicit user preference.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Language Detection
# ─────────────────────────────────────────────────────────────────────────────

class DetectLanguageRequest(BaseModel):
    """
    Detect the language of a raw text string.
    Used by any service before saving or routing user-generated content.
    """
    text:       str            = Field(min_length=1, max_length=5000)
    user_id:    Optional[uuid.UUID] = Field(
        default=None,
        description="When provided, the detection is logged and can update preferences.",
    )
    channel:    Optional[str]  = Field(
        default=None,
        description="Source channel: sms | whatsapp | call | web | mobile | ivr",
    )
    session_id: Optional[str]  = Field(
        default=None,
        description="Channel session ID for linkage in detection logs.",
    )
    update_preference: bool    = Field(
        default=False,
        description="If True and confidence ≥ threshold, update user's preferred_language.",
    )


class DetectLanguageResponse(BaseModel):
    """Result of language detection on a text input."""
    detected_language: str
    confidence:        float   = Field(ge=0.0, le=1.0)
    is_supported:      bool
    alternatives:      List[Dict[str, float]] = Field(
        default_factory=list,
        description="Other candidate languages with their confidence scores.",
    )
    preference_updated: bool = False


class ChannelDetectRequest(BaseModel):
    """
    Detect language from a full channel session (SMS thread, WhatsApp conversation,
    call transcript). Concatenates messages and runs detection on the combined text.
    Higher accuracy than single-message detection.
    """
    messages:          List[str]      = Field(
        min_length=1,
        description="Ordered list of message texts from the channel session.",
    )
    channel:           str            = Field(
        description="Channel type: sms | whatsapp | call | web | mobile | ivr",
    )
    user_id:           Optional[uuid.UUID] = None
    session_id:        Optional[str]       = None
    update_preference: bool                = Field(default=True)


class DetectionLogResponse(BaseModel):
    """Single detection log entry."""
    model_config = ConfigDict(from_attributes=True)

    id:                 uuid.UUID
    user_id:            Optional[uuid.UUID]
    session_id:         Optional[str]
    channel:            str
    detection_source:   str
    detected_language:  str
    confidence:         float
    text_sample:        Optional[str]
    preference_updated: bool
    created_at:         datetime


class DetectionLogListResponse(BaseModel):
    items: List[DetectionLogResponse]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Translation
# ─────────────────────────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    """Translate a single string."""
    text:          str           = Field(min_length=1, max_length=10000)
    target_language: str         = Field(min_length=2, max_length=10,
                                         description="BCP-47 target language code.")
    source_language: Optional[str] = Field(
        default=None,
        description="BCP-47 source language. Auto-detected when omitted.",
    )
    context:       Optional[str] = Field(
        default=None, max_length=200,
        description="Domain hint for context-aware translation: 'grievance' | 'legal' | 'general'",
    )


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str        # detected or provided
    target_language: str
    provider:        str        # 'google' | 'deepl' | 'libre'
    cached:          bool = False


class BatchTranslateRequest(BaseModel):
    """
    Translate multiple strings in one call.
    All strings are translated to the same target language.
    Most efficient for rendering multi-field notification templates.
    """
    texts:           List[str]     = Field(min_length=1, max_items=50)
    target_language: str           = Field(min_length=2, max_length=10)
    source_language: Optional[str] = None


class BatchTranslateResponse(BaseModel):
    results:         List[TranslateResponse]
    target_language: str
    provider:        str


# ─────────────────────────────────────────────────────────────────────────────
# Internal (service-to-service)
# ─────────────────────────────────────────────────────────────────────────────

class InternalUserLanguageResponse(BaseModel):
    """
    Minimal language info returned to other services for content rendering.
    E.g. notification_service calls this to know what language to render a template in.
    """
    user_id:            uuid.UUID
    preferred_language: str
    fallback_language:  str
    has_preference:     bool   # False if using platform default


class InternalDetectAndUpdateRequest(BaseModel):
    """
    Called by feedback_service or channel services when a Consumer submits content.
    Detects language from text, logs it, and optionally updates user preference.
    """
    text:              str
    user_id:           Optional[uuid.UUID] = None
    channel:           str
    session_id:        Optional[str]       = None
    update_preference: bool                = True
