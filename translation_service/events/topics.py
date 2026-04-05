# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  events/topics.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/topics.py — Kafka topic and event type constants.

CONSUMES: riviwa.user.events  (auth_service)
  user.registered         → auto-create default language preference (sw → en)
  user.deactivated        → soft-delete preference row (GDPR)
  user.banned             → soft-delete preference row (GDPR)

PUBLISHES: riviwa.translation.events
  language.preference_set          — user explicitly chose a language in settings
  language.preference_auto_updated — language auto-updated from detection
  language.detected                — language detection ran on user text/session
  translation.completed            — a translation request was served
═══════════════════════════════════════════════════════════════════════════════
Consumers of riviwa.translation.events:
  · Admin dashboard    — language distribution analytics across the platform
  · Notification svc   — knows which language to render templates in
  · Feedback svc       — routes SMS/WhatsApp sessions in the right language
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


class KafkaTopics:
    # Inbound
    USER_EVENTS        = "riviwa.user.events"
    # Outbound
    TRANSLATION_EVENTS = "riviwa.translation.events"


class UserEvents:
    """User lifecycle events consumed from riviwa.user.events (auth_service)."""
    REGISTERED  = "user.registered"
    DEACTIVATED = "user.deactivated"
    BANNED      = "user.banned"


class TranslationEvents:
    """
    Events published by translation_service on riviwa.translation.events.

    language.preference_set
    ─────────────────────────────────────────────────────────────────────────
    Fired when a user explicitly selects a language in the app settings.
    Payload:
      user_id           — UUID of the user
      previous_language — language code before the change  (may be null)
      new_language      — language code after the change
      fallback_language — fallback code (en by default)
      source            — "user_settings" | "mobile_app"
      channel           — channel where the change was triggered (optional)

    language.preference_auto_updated
    ─────────────────────────────────────────────────────────────────────────
    Fired when the language is updated automatically from detection
    (i.e. the system detected what language the user is writing in).
    Payload:
      user_id           — UUID of the user
      previous_language — language code before the change
      new_language      — detected + applied language code
      confidence        — detection confidence score (0.0–1.0)
      source            — "text_detection" | "channel_session" | "device_locale"
      channel           — channel where detection happened (optional)
      session_id        — channel session ID (optional)

    language.detected
    ─────────────────────────────────────────────────────────────────────────
    Fired on every detection call, even when the preference is NOT updated.
    Useful for analytics — tracks which languages are being written across
    all incoming submissions.
    Payload:
      user_id           — UUID (may be null for anonymous submissions)
      detected_language — detected language code
      confidence        — detection confidence score
      source            — "text_detection" | "channel_session" | "device_locale"
      channel           — channel (optional)
      session_id        — session ID (optional)
      preference_updated — bool — whether this detection triggered a pref update

    translation.completed
    ─────────────────────────────────────────────────────────────────────────
    Fired after every successful translation (cache miss — actual provider call).
    Useful for usage analytics and cost tracking.
    Payload:
      source_language   — detected or supplied source language code
      target_language   — requested target language code
      provider          — "google" | "deepl" | "microsoft" | "nllb" | "libretranslate"
      cached            — bool (False here — only fires on actual provider calls)
      char_count        — number of characters translated
    """
    PREFERENCE_SET          = "language.preference_set"
    PREFERENCE_AUTO_UPDATED = "language.preference_auto_updated"
    DETECTED                = "language.detected"
    TRANSLATION_COMPLETED   = "translation.completed"
