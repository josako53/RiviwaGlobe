"""
services/voice_ai_service.py — Voice input pipeline for AI conversations.
Integrates MinIO object storage so every audio turn is persisted before
transcription — matching the feedback_service VoiceService pattern.

Full pipeline:
  audio bytes
    → Whisper STT  (transcription + language detection in one call)
    → translation_service /detect  (confirm language from transcript text)
    → if language not in [sw, en]  → translate to English via translation_service
    → ConversationService.process_message  (AI reasoning, extraction, auto-submit)
    → if translated  → translate AI reply back to original language
    → return enriched response with transcript + detected_language + reply

Design decisions:
  - Whisper verbose_json gives us language in the same API call as transcription
    (no extra round trip). We cross-check with translation_service text detection
    for short recordings where Whisper may be less certain.
  - Processing language is always English or Swahili — the AI LLM performs best
    in these languages. All other languages are translated before the AI sees them.
  - Reply translation is best-effort: if translation_service is down, we return
    the English reply with a note rather than failing the whole request.
  - Twilio recording download is here (not in STTService) so the full voice
    pipeline is self-contained.
"""
from __future__ import annotations

import io
import uuid
from typing import Optional
import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from services.stt_service import STTService, _MIME_TO_EXT
from services.conversation_service import ConversationService

log = structlog.get_logger(__name__)

# Languages the AI handles natively — no translation needed
_NATIVE_LANGUAGES = {"sw", "en"}

# Minimum Whisper confidence before we trust its language detection
_MIN_WHISPER_LANG_CONFIDENCE = 0.40

# Translation service base URL
_TRANSLATION_URL = settings.TRANSLATION_SERVICE_URL
_INTERNAL_HEADERS = {
    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}


class VoiceAIService:
    """
    Orchestrates: audio → STT → language detection → optional translation →
                  AI conversation → optional reply translation.
    """

    def __init__(self) -> None:
        self.stt = STTService()

    # ─── MinIO storage ────────────────────────────────────────────────────────

    async def _store_audio(
        self,
        audio_bytes:     bytes,
        content_type:    str,
        conversation_id: uuid.UUID,
        turn_index:      int,
    ) -> str:
        """
        Upload audio bytes to MinIO and return a permanent object URL.

        Path: ai-voice/conversations/{conv_id}/turn_{n:04d}.{ext}

        Returns empty string on any storage failure — voice pipeline continues
        without persisted audio rather than blocking the user interaction.
        """
        ext    = _MIME_TO_EXT.get(content_type.split(";")[0].strip(), "webm")
        bucket = "ai-voice"
        key    = f"conversations/{conversation_id}/turn_{turn_index:04d}.{ext}"
        try:
            import aiobotocore.session as aio_session  # type: ignore
            session = aio_session.get_session()
            async with session.create_client(
                "s3",
                endpoint_url=settings.MINIO_ENDPOINT,
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
            ) as client:
                # Create bucket if it doesn't exist
                try:
                    await client.head_bucket(Bucket=bucket)
                except Exception:
                    await client.create_bucket(Bucket=bucket)

                await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=audio_bytes,
                    ContentType=content_type,
                )
            audio_url = f"{settings.MINIO_ENDPOINT}/{bucket}/{key}"
            log.info("voice_ai.audio_stored", key=key, bytes=len(audio_bytes))
            return audio_url
        except Exception as exc:
            log.warning("voice_ai.audio_store_failed", error=str(exc))
            return ""

    def _current_turn_index(self, db_conv) -> int:
        """Return the 0-based index for the next user turn."""
        turns = db_conv.get_turns() if db_conv else []
        return sum(1 for t in turns if t.get("role") == "user")

    # ─── Public entry point ───────────────────────────────────────────────────

    async def process_voice_turn(
        self,
        audio_bytes:     bytes,
        content_type:    str,
        conversation_id: uuid.UUID,
        db:              AsyncSession,
    ) -> dict:
        """
        Full voice-to-AI-reply pipeline.

        Returns a dict extending the standard chat response with:
          transcript        — raw transcription from Whisper
          detected_language — BCP-47 code (e.g. "sw", "en", "fr")
          stt_confidence    — Whisper confidence proxy (0–1)
          translated        — True if the transcript was translated before AI
          original_reply    — English/Swahili AI reply (before back-translation)
        """
        # 1. Persist audio to MinIO before transcribing (audit trail + replay)
        from repositories.conversation_repo import ConversationRepository
        conv_for_index = await ConversationRepository(db).get(conversation_id)
        turn_idx  = self._current_turn_index(conv_for_index)
        audio_url = await self._store_audio(audio_bytes, content_type, conversation_id, turn_idx)

        # 2. Transcribe + detect language
        transcript, whisper_lang, stt_conf = await self.stt.transcribe_with_detection(
            audio_bytes, content_type
        )

        if not transcript:
            return {
                "error":             "STT_FAILED",
                "message":           "Could not transcribe audio. Please try again.",
                "transcript":        "",
                "detected_language": whisper_lang or "sw",
                "stt_confidence":    0.0,
                "audio_url":         audio_url,
            }

        # 2. Confirm language via translation_service text detection
        #    (more reliable than Whisper for short audio)
        confirmed_lang = await self._confirm_language(transcript, whisper_lang, stt_conf)

        # 4. Translate to processing language if not native
        processing_text = transcript
        translated      = False
        if confirmed_lang not in _NATIVE_LANGUAGES:
            translated_text = await self._translate(transcript, source=confirmed_lang, target="en")
            if translated_text:
                processing_text = translated_text
                translated      = True
                log.info("voice_ai.translated_input",
                         from_lang=confirmed_lang, chars=len(processing_text))

        # 5. Feed into AI conversation (audio_url stored in the turn record)
        conv_svc = ConversationService(db=db)
        conv, reply, submitted, feedback_list = await conv_svc.process_message(
            conversation_id=conversation_id,
            message=processing_text,
            audio_url=audio_url or None,
        )
        original_reply = reply

        # 6. Translate reply back if input was translated
        final_reply = reply
        if translated and confirmed_lang not in _NATIVE_LANGUAGES:
            back = await self._translate(reply, source="en", target=confirmed_lang)
            if back:
                final_reply = back

        # Build response (superset of standard chat response)
        extracted = conv.get_extracted()
        fb_list   = [
            {
                "feedback_id":   f.get("feedback_id", ""),
                "unique_ref":    f.get("unique_ref", ""),
                "feedback_type": f.get("feedback_type", ""),
            }
            for f in (feedback_list or [])
        ]
        return {
            # Standard chat fields
            "conversation_id":    str(conv.id),
            "reply":              final_reply,
            "status":             conv.status.value,
            "stage":              conv.stage.value,
            "turn_count":         conv.turn_count,
            "confidence":         float(extracted.get("confidence", 0.0)),
            "language":           conv.language,
            "submitted":          submitted,
            "submitted_feedback": fb_list,
            "org_id":             str(conv.org_id) if conv.org_id else None,
            "project_name":       conv.project_name,
            "is_urgent":          conv.is_urgent,
            "incharge_name":      conv.incharge_name,
            "incharge_phone":     conv.incharge_phone,
            # Voice-specific fields
            "transcript":         transcript,
            "detected_language":  confirmed_lang,
            "stt_confidence":     round(stt_conf, 3),
            "translated":         translated,
            "original_reply":     original_reply,
            "audio_url":          audio_url or None,
        }

    async def download_twilio_recording(self, recording_url: str) -> Optional[bytes]:
        """Download a Twilio recording MP3 using Basic Auth credentials."""
        return await self.stt.download_twilio_recording(recording_url)

    # ─── Private helpers ──────────────────────────────────────────────────────

    async def _confirm_language(
        self,
        text:        str,
        whisper_lang: str,
        whisper_conf: float,
    ) -> str:
        """
        Cross-check Whisper's language detection with translation_service text detection.
        Uses Whisper result when it's highly confident or when text is too short for
        text-based detection (< 20 chars). Falls back to Whisper on any error.
        """
        if len(text) < 20 or whisper_conf >= 0.80:
            return whisper_lang

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(
                    f"{_TRANSLATION_URL}/detect",
                    json={"text": text[:500]},
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    data      = r.json()
                    text_lang = data.get("detected_language", whisper_lang)
                    text_conf = data.get("confidence", 0.0)

                    # If both agree, high confidence result
                    if text_lang == whisper_lang:
                        return whisper_lang

                    # Prefer text detection when it's more confident than Whisper
                    if text_conf > whisper_conf:
                        log.info("voice_ai.lang_override",
                                 whisper=whisper_lang, text_detect=text_lang,
                                 text_conf=text_conf, whisper_conf=whisper_conf)
                        return text_lang
        except Exception as exc:
            log.warning("voice_ai.lang_confirm_failed", error=str(exc))

        return whisper_lang

    async def _translate(self, text: str, source: str, target: str) -> Optional[str]:
        """
        Call translation_service to translate text.
        Returns translated text, or None on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{_TRANSLATION_URL}/translate",
                    json={
                        "text":            text,
                        "source_language": source,
                        "target_language": target,
                    },
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    return r.json().get("translated_text")
                log.warning("voice_ai.translate_failed",
                            status=r.status_code, source=source, target=target)
        except Exception as exc:
            log.warning("voice_ai.translate_error", error=str(exc))
        return None
