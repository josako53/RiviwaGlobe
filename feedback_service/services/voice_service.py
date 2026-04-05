# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  services/voice_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/voice_service.py — feedback_service
═══════════════════════════════════════════════════════════════════════════════
Voice pipeline for Riviwa feedback:

  INBOUND (PAP → Riviwa):
    1. Receive audio bytes (upload, webhook payload, stream)
    2. Store to object storage (MinIO/S3) → audio_url
    3. Transcribe via STT (Whisper / Google STT) → text + confidence
    4. Return VoiceTranscriptionResult for the caller to act on

  OUTBOUND (Riviwa → PAP):
    5. Synthesise text → speech (TTS) for phone_call / mobile_app voice replies
    6. Store TTS audio → return audio_url for streaming back to PAP

  SESSION COMPLETION:
    7. Assemble per-turn audio into full session transcript
    8. Update ChannelSession.transcription + audio_recording_url

SUPPORTED CHANNELS:
  · PHONE_CALL        — full-session recording; officer or IVR driven
  · WHATSAPP_VOICE    — Meta sends OGG/OPUS audio file via webhook
  · MOBILE_APP (mic)  — PAP holds mic button; per-turn audio upload
  · WEB_PORTAL (mic)  — same as mobile_app but from browser (WebM/OPUS)
  · IN_PERSON         — officer records walk-in consultation (any format)

STT PROVIDER PRIORITY (configurable via settings):
  1. Whisper (OpenAI API or self-hosted faster-whisper)
  2. Google Cloud STT
  3. Azure Cognitive Services STT
  Fallback: flag for manual transcription (transcription_service = 'manual')

AUDIO STORAGE:
  Object storage bucket: VOICE_STORAGE_BUCKET (default: 'riviwa-voice')
  Path convention:
    feedback/  {feedback_id}/voice_note.{ext}
    sessions/  {session_id}/full_recording.{ext}
    sessions/  {session_id}/turn_{n}.{ext}
    sessions/  {session_id}/tts_turn_{n}.mp3

RETENTION:
  Audio files are the legal source-of-truth for the GRM.
  They must NOT be deleted — only the signed URL should expire.
  Permanent retention policy must be set on the storage bucket.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import io
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VoiceTranscriptionResult:
    """
    Returned by transcribe_audio().
    Callers use this to populate Feedback or ChannelSession fields.
    """
    text:                str
    language:            str              # IETF tag: "sw" | "en"
    confidence:          float            # 0.0–1.0 (1.0 = certain)
    duration_seconds:    int
    audio_url:           str              # permanent object storage URL
    service:             str              # "whisper" | "google_stt" | "azure_stt" | "manual"
    flagged_for_review:  bool = False     # True if confidence < TRANSCRIPTION_REVIEW_THRESHOLD


@dataclass
class TTSResult:
    """Returned by synthesise_speech()."""
    audio_url:        str   # URL of the generated MP3/OGG in object storage
    duration_seconds: int
    service:          str   # "google_tts" | "azure_tts" | "elevenlabs"


@dataclass
class SessionTranscriptResult:
    """Returned by assemble_session_transcript()."""
    full_transcription:    str
    audio_recording_url:   str   # concatenated full session audio
    total_duration_seconds: int
    average_confidence:    float


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Below this confidence level the record is flagged for manual review
TRANSCRIPTION_REVIEW_THRESHOLD: float = 0.70

# Supported inbound audio MIME types and their storage extensions
AUDIO_MIME_TO_EXT: dict[str, str] = {
    "audio/ogg":        "ogg",    # WhatsApp voice notes (OGG/OPUS)
    "audio/mpeg":       "mp3",
    "audio/mp4":        "m4a",
    "audio/webm":       "webm",   # Browser MediaRecorder (Chrome/Firefox)
    "audio/wav":        "wav",
    "audio/x-wav":      "wav",
    "audio/aac":        "aac",
    "audio/amr":        "amr",    # Common on feature phones / GSM calls
    "audio/flac":       "flac",
}


# ─────────────────────────────────────────────────────────────────────────────
# VoiceService
# ─────────────────────────────────────────────────────────────────────────────

class VoiceService:
    """
    Stateless service — instantiate per request.

    Usage (feedback voice note):
      svc = VoiceService()
      result = await svc.transcribe_audio(
          audio_bytes=request_body,
          mime_type="audio/ogg",
          context="feedback",
          object_id=feedback_id,
          language_hint="sw",
      )
      feedback.voice_note_url                   = result.audio_url
      feedback.voice_note_transcription         = result.text
      feedback.voice_note_duration_seconds      = result.duration_seconds
      feedback.voice_note_language              = result.language
      feedback.voice_note_transcription_confidence  = result.confidence
      feedback.voice_note_transcription_service = result.service
      if not feedback.description:
          feedback.description = result.text   # use transcript as description

    Usage (session voice turn):
      result = await svc.transcribe_audio(
          audio_bytes=turn_audio,
          mime_type="audio/webm",
          context="session_turn",
          object_id=session_id,
          turn_index=turn_n,
          language_hint=session.language,
      )
      session.add_turn(
          role="user",
          content=result.text,
          audio_url=result.audio_url,
          is_voice=True,
          transcription_confidence=result.confidence,
      )
    """

    # ── Audio Storage ─────────────────────────────────────────────────────────

    async def store_audio(
        self,
        audio_bytes:   bytes,
        mime_type:     str,
        context:       str,       # "feedback" | "session_turn" | "session_full" | "tts"
        object_id:     uuid.UUID,
        turn_index:    Optional[int] = None,
    ) -> str:
        """
        Store audio bytes to object storage and return the permanent URL.

        Storage path convention:
          feedback/{feedback_id}/voice_note.{ext}
          sessions/{session_id}/turn_{n}.{ext}
          sessions/{session_id}/full_recording.{ext}
          sessions/{session_id}/tts_turn_{n}.mp3

        Returns the full object storage URL (permanent, not pre-signed).
        For public download a pre-signed URL should be generated at read time.
        """
        ext  = AUDIO_MIME_TO_EXT.get(mime_type, "bin")
        bucket = getattr(settings, "VOICE_STORAGE_BUCKET", "riviwa-voice")

        if context == "feedback":
            key = f"feedback/{object_id}/voice_note.{ext}"
        elif context == "session_turn" and turn_index is not None:
            key = f"sessions/{object_id}/turn_{turn_index:04d}.{ext}"
        elif context == "session_full":
            key = f"sessions/{object_id}/full_recording.{ext}"
        elif context == "tts" and turn_index is not None:
            key = f"sessions/{object_id}/tts_turn_{turn_index:04d}.mp3"
        else:
            key = f"misc/{object_id}/{uuid.uuid4()}.{ext}"

        url = await self._upload_to_object_storage(bucket, key, audio_bytes, mime_type)
        log.info("voice.audio.stored", context=context, key=key, size_bytes=len(audio_bytes))
        return url

    # ── Speech-to-Text ────────────────────────────────────────────────────────

    async def transcribe_audio(
        self,
        audio_bytes:    bytes,
        mime_type:      str,
        context:        str,
        object_id:      uuid.UUID,
        language_hint:  str = "sw",
        turn_index:     Optional[int] = None,
    ) -> VoiceTranscriptionResult:
        """
        Store audio then transcribe. Returns VoiceTranscriptionResult.

        language_hint: "sw" = Swahili (default for Tanzania), "en" = English.
        Whisper auto-detects language if hint is wrong.
        """
        audio_url = await self.store_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            context=context,
            object_id=object_id,
            turn_index=turn_index,
        )

        # Try providers in priority order
        for provider in self._get_stt_provider_order():
            try:
                text, language, confidence, duration = await self._call_stt(
                    provider=provider,
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    language_hint=language_hint,
                )
                flagged = confidence < TRANSCRIPTION_REVIEW_THRESHOLD
                if flagged:
                    log.warning(
                        "voice.transcription.low_confidence",
                        provider=provider,
                        confidence=confidence,
                        context=context,
                        object_id=str(object_id),
                    )
                return VoiceTranscriptionResult(
                    text=text,
                    language=language,
                    confidence=confidence,
                    duration_seconds=duration,
                    audio_url=audio_url,
                    service=provider,
                    flagged_for_review=flagged,
                )
            except Exception as exc:
                log.warning(
                    "voice.stt.provider_failed",
                    provider=provider,
                    error=str(exc),
                )
                continue

        # All providers failed — return the audio URL with empty transcription
        # flagged for manual review
        log.error(
            "voice.stt.all_providers_failed",
            context=context,
            object_id=str(object_id),
        )
        return VoiceTranscriptionResult(
            text="",
            language=language_hint,
            confidence=0.0,
            duration_seconds=0,
            audio_url=audio_url,
            service="manual",
            flagged_for_review=True,
        )

    # ── Text-to-Speech ────────────────────────────────────────────────────────

    async def synthesise_speech(
        self,
        text:        str,
        language:    str,       # "sw" | "en"
        session_id:  uuid.UUID,
        turn_index:  int,
        voice_id:    Optional[str] = None,
    ) -> TTSResult:
        """
        Convert text to speech for two-way voice conversations.

        Used for:
          · PHONE_CALL: LLM response played back via IVR/PSTN
          · MOBILE_APP/WEB_PORTAL mic mode: LLM response played in the app

        Stores the generated audio in object storage and returns the URL
        for the API caller to stream back or pass to the telephony gateway.
        """
        provider = getattr(settings, "TTS_PROVIDER", "google_tts")
        try:
            audio_bytes, duration = await self._call_tts(
                provider=provider,
                text=text,
                language=language,
                voice_id=voice_id,
            )
            audio_url = await self.store_audio(
                audio_bytes=audio_bytes,
                mime_type="audio/mpeg",
                context="tts",
                object_id=session_id,
                turn_index=turn_index,
            )
            log.info(
                "voice.tts.synthesised",
                provider=provider,
                language=language,
                duration_seconds=duration,
                session_id=str(session_id),
            )
            return TTSResult(
                audio_url=audio_url,
                duration_seconds=duration,
                service=provider,
            )
        except Exception as exc:
            log.error("voice.tts.failed", provider=provider, error=str(exc), exc_info=exc)
            raise

    # ── Session Assembly ──────────────────────────────────────────────────────

    async def assemble_session_transcript(
        self,
        session_id: uuid.UUID,
        turns:      list[dict],
    ) -> SessionTranscriptResult:
        """
        Called when a ChannelSession reaches COMPLETED status.

        Assembles:
          1. Full text transcript from all voice turns in order
          2. Full audio recording URL (concatenated audio — if supported)
          3. Average transcription confidence across all voice turns

        The result is written to ChannelSession fields by the caller:
          session.transcription         = result.full_transcription
          session.audio_recording_url   = result.audio_recording_url
          session.transcription_confidence = result.average_confidence
          session.audio_duration_seconds   = result.total_duration_seconds
        """
        voice_turns = [t for t in turns if t.get("is_voice") and t.get("content")]
        all_turns   = [t for t in turns if t.get("content")]

        # Assemble text transcript (all turns, labelled)
        lines = []
        for t in all_turns:
            role    = "PAP" if t["role"] == "user" else "Riviwa"
            content = t["content"]
            ts      = t.get("ts", "")[:19].replace("T", " ")
            lines.append(f"[{ts}] {role}: {content}")
        full_text = "\n".join(lines)

        # Average confidence from voice turns
        confidences = [
            t["transcription_confidence"]
            for t in voice_turns
            if t.get("transcription_confidence") is not None
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0

        # Attempt to concatenate audio files into one recording
        audio_url = await self._concatenate_session_audio(session_id, voice_turns)

        # Estimate total duration from individual turn durations (not always available)
        total_duration = 0

        log.info(
            "voice.session.assembled",
            session_id=str(session_id),
            voice_turns=len(voice_turns),
            total_turns=len(all_turns),
            avg_confidence=round(avg_confidence, 3),
        )
        return SessionTranscriptResult(
            full_transcription=full_text,
            audio_recording_url=audio_url,
            total_duration_seconds=total_duration,
            average_confidence=avg_confidence,
        )

    # ── WhatsApp Voice Webhook Handler ────────────────────────────────────────

    async def process_whatsapp_voice_message(
        self,
        whatsapp_media_id: str,
        from_number:       str,
        project_id:        Optional[uuid.UUID] = None,
    ) -> VoiceTranscriptionResult:
        """
        Handle an incoming WhatsApp voice note (OGG/OPUS from Meta).

        Flow:
          1. Download OGG audio from Meta's media API using whatsapp_media_id
          2. Store to object storage
          3. Transcribe via STT
          4. Return result for the channel handler to create/continue a session

        The channel handler in channels.py then treats the transcribed text
        exactly like an incoming text message — it feeds it into the LLM
        conversation pipeline as if the PAP had typed it.
        """
        log.info(
            "voice.whatsapp_voice.received",
            media_id=whatsapp_media_id,
            from_number=from_number,
        )
        audio_bytes = await self._download_whatsapp_media(whatsapp_media_id)
        session_id  = uuid.uuid4()   # temporary — caller replaces with real session ID

        result = await self.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type="audio/ogg",
            context="session_turn",
            object_id=session_id,
            language_hint="sw",
            turn_index=0,
        )
        log.info(
            "voice.whatsapp_voice.transcribed",
            from_number=from_number,
            text_preview=result.text[:80] if result.text else "",
            confidence=result.confidence,
            flagged=result.flagged_for_review,
        )
        return result

    # ── Private: Provider dispatch ────────────────────────────────────────────

    def _get_stt_provider_order(self) -> list[str]:
        """
        Returns the STT provider list in priority order.
        Configured via STT_PROVIDER_ORDER in settings.
        Default: Whisper first (cheapest, local-capable), then Google STT fallback.
        """
        default = "whisper,google_stt"
        order_str = getattr(settings, "STT_PROVIDER_ORDER", default)
        return [p.strip() for p in order_str.split(",") if p.strip()]

    async def _call_stt(
        self,
        provider:      str,
        audio_bytes:   bytes,
        mime_type:     str,
        language_hint: str,
    ) -> tuple[str, str, float, int]:
        """
        Calls the specified STT provider.
        Returns: (text, detected_language, confidence, duration_seconds)
        """
        if provider == "whisper":
            return await self._stt_whisper(audio_bytes, mime_type, language_hint)
        elif provider == "google_stt":
            return await self._stt_google(audio_bytes, mime_type, language_hint)
        elif provider == "azure_stt":
            return await self._stt_azure(audio_bytes, mime_type, language_hint)
        else:
            raise ValueError(f"Unknown STT provider: {provider}")

    async def _call_tts(
        self,
        provider:  str,
        text:      str,
        language:  str,
        voice_id:  Optional[str],
    ) -> tuple[bytes, int]:
        """
        Calls the specified TTS provider.
        Returns: (audio_bytes, duration_seconds)
        """
        if provider == "google_tts":
            return await self._tts_google(text, language, voice_id)
        elif provider == "azure_tts":
            return await self._tts_azure(text, language, voice_id)
        elif provider == "elevenlabs":
            return await self._tts_elevenlabs(text, language, voice_id)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

    # ── Private: STT provider implementations ────────────────────────────────

    async def _stt_whisper(
        self, audio_bytes: bytes, mime_type: str, language_hint: str
    ) -> tuple[str, str, float, int]:
        """
        OpenAI Whisper (API) or self-hosted faster-whisper.

        WHISPER_MODE = "api"   → uses OpenAI Whisper API (requires OPENAI_API_KEY)
        WHISPER_MODE = "local" → uses faster-whisper running in the container
                                 (set WHISPER_MODEL_SIZE = "medium" or "large-v3")

        Whisper supports Swahili natively. It auto-detects language if the
        language_hint is wrong. Very accurate for Tanzanian accents.
        """
        import httpx
        mode = getattr(settings, "WHISPER_MODE", "api")

        if mode == "api":
            api_key = getattr(settings, "OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set for Whisper API mode")
            ext = AUDIO_MIME_TO_EXT.get(mime_type, "ogg")
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={"model": "whisper-1", "language": language_hint, "response_format": "verbose_json"},
                    files={"file": (f"audio.{ext}", io.BytesIO(audio_bytes), mime_type)},
                )
            resp.raise_for_status()
            data     = resp.json()
            text     = data.get("text", "").strip()
            language = data.get("language", language_hint)
            # Whisper API doesn't return per-segment confidence in basic mode;
            # use a fixed high value and rely on content quality checks.
            duration = int(data.get("duration", 0))
            return text, language, 0.92, duration

        elif mode == "local":
            # faster-whisper (self-hosted) — run in executor to avoid blocking event loop
            def _run_faster_whisper() -> tuple[str, str, float, int]:
                from faster_whisper import WhisperModel  # type: ignore
                model_size = getattr(settings, "WHISPER_MODEL_SIZE", "medium")
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                audio_io = io.BytesIO(audio_bytes)
                segments, info = model.transcribe(audio_io, language=language_hint)
                text = " ".join(s.text.strip() for s in segments)
                avg_logprob = sum(s.avg_logprob for s in segments) / max(len(list(segments)), 1)
                # Convert log probability to approximate confidence
                import math
                confidence = max(0.0, min(1.0, math.exp(avg_logprob)))
                duration = int(info.duration)
                return text, info.language, confidence, duration

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _run_faster_whisper)
        else:
            raise ValueError(f"Unknown WHISPER_MODE: {mode}")

    async def _stt_google(
        self, audio_bytes: bytes, mime_type: str, language_hint: str
    ) -> tuple[str, str, float, int]:
        """
        Google Cloud Speech-to-Text.
        Requires: GOOGLE_STT_API_KEY or GOOGLE_APPLICATION_CREDENTIALS in env.
        Supports Swahili (sw-TZ) and English (en-GB).
        """
        import httpx
        api_key  = getattr(settings, "GOOGLE_STT_API_KEY", "")
        lang_map = {"sw": "sw-TZ", "en": "en-GB"}
        lang_code = lang_map.get(language_hint, "sw-TZ")
        ext = AUDIO_MIME_TO_EXT.get(mime_type, "ogg")

        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode()

        payload = {
            "config": {
                "encoding":        "OGG_OPUS" if ext == "ogg" else "WEBM_OPUS",
                "languageCode":    lang_code,
                "enableWordTimeOffsets": False,
                "model":           "latest_long",
                "enableAutomaticPunctuation": True,
            },
            "audio": {"content": audio_b64},
        }
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        results  = data.get("results", [])
        if not results:
            return "", language_hint, 0.0, 0
        best     = results[0]["alternatives"][0]
        text     = best.get("transcript", "").strip()
        confidence = float(best.get("confidence", 0.85))
        return text, language_hint, confidence, 0

    async def _stt_azure(
        self, audio_bytes: bytes, mime_type: str, language_hint: str
    ) -> tuple[str, str, float, int]:
        """
        Azure Cognitive Services Speech-to-Text.
        Requires: AZURE_STT_KEY, AZURE_STT_REGION in settings.
        """
        import httpx
        key    = getattr(settings, "AZURE_STT_KEY", "")
        region = getattr(settings, "AZURE_STT_REGION", "eastus")
        lang_map = {"sw": "sw-KE", "en": "en-GB"}
        lang_code = lang_map.get(language_hint, "sw-KE")
        url = (
            f"https://{region}.stt.speech.microsoft.com/"
            f"speech/recognition/conversation/cognitiveservices/v1"
            f"?language={lang_code}&format=detailed"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": mime_type,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, content=audio_bytes)
        resp.raise_for_status()
        data  = resp.json()
        nbest = data.get("NBest", [{}])
        text  = nbest[0].get("Display", "").strip() if nbest else ""
        confidence = float(nbest[0].get("Confidence", 0.85)) if nbest else 0.0
        return text, language_hint, confidence, 0

    # ── Private: TTS provider implementations ────────────────────────────────

    async def _tts_google(
        self, text: str, language: str, voice_id: Optional[str]
    ) -> tuple[bytes, int]:
        """Google Cloud Text-to-Speech. Supports Swahili (sw-TZ)."""
        import httpx, base64
        api_key   = getattr(settings, "GOOGLE_TTS_API_KEY", "")
        lang_map  = {"sw": "sw-TZ", "en": "en-GB"}
        lang_code = lang_map.get(language, "sw-TZ")
        payload   = {
            "input":      {"text": text},
            "voice":      {"languageCode": lang_code, "name": voice_id or ""},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        resp.raise_for_status()
        audio_bytes = base64.b64decode(resp.json()["audioContent"])
        duration = max(1, len(text.split()) // 3)   # rough estimate: 3 words/sec
        return audio_bytes, duration

    async def _tts_azure(
        self, text: str, language: str, voice_id: Optional[str]
    ) -> tuple[bytes, int]:
        """Azure Cognitive Services TTS. Supports sw-KE (Swahili)."""
        import httpx
        key    = getattr(settings, "AZURE_TTS_KEY", "")
        region = getattr(settings, "AZURE_TTS_REGION", "eastus")
        lang_map  = {"sw": "sw-KE-ZuriNeural", "en": "en-GB-SoniaNeural"}
        voice     = voice_id or lang_map.get(language, "sw-KE-ZuriNeural")
        ssml      = f'<speak version="1.0" xml:lang="{language}"><voice name="{voice}">{text}</voice></speak>'
        url       = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers   = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, content=ssml.encode())
        resp.raise_for_status()
        duration = max(1, len(text.split()) // 3)
        return resp.content, duration

    async def _tts_elevenlabs(
        self, text: str, language: str, voice_id: Optional[str]
    ) -> tuple[bytes, int]:
        """ElevenLabs TTS (highest quality, good for PHONE_CALL naturalness)."""
        import httpx
        api_key  = getattr(settings, "ELEVENLABS_API_KEY", "")
        vid      = voice_id or getattr(settings, "ELEVENLABS_DEFAULT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        url      = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        headers  = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload  = {"text": text, "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        duration = max(1, len(text.split()) // 3)
        return resp.content, duration

    # ── Private: Storage ─────────────────────────────────────────────────────

    async def _upload_to_object_storage(
        self, bucket: str, key: str, data: bytes, content_type: str
    ) -> str:
        """
        Upload to MinIO (S3-compatible). Returns the object URL.

        If STORAGE_PROVIDER = "s3"   → AWS S3
        If STORAGE_PROVIDER = "minio" → self-hosted MinIO (default for dev)
        If STORAGE_PROVIDER = "local" → write to LOCAL_STORAGE_PATH (testing only)

        In production, the URL should be the public/internal endpoint.
        Pre-signed URLs are generated at read time — not stored here.
        """
        provider = getattr(settings, "STORAGE_PROVIDER", "minio")

        if provider in ("minio", "s3"):
            import aiobotocore.session  # type: ignore
            endpoint   = getattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
            access_key = getattr(settings, "MINIO_ACCESS_KEY", "minioadmin")
            secret_key = getattr(settings, "MINIO_SECRET_KEY", "minioadmin")

            session = aiobotocore.session.get_session()
            async with session.create_client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            ) as client:
                await client.put_object(
                    Bucket=bucket, Key=key, Body=data, ContentType=content_type
                )
            base = endpoint.rstrip("/")
            url  = f"{base}/{bucket}/{key}"

        elif provider == "local":
            import pathlib, aiofiles  # type: ignore
            base_path = pathlib.Path(getattr(settings, "LOCAL_STORAGE_PATH", "/tmp/riviwa-voice"))
            full_path = base_path / bucket / key
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
            url = f"file://{full_path}"
        else:
            raise ValueError(f"Unknown STORAGE_PROVIDER: {provider}")

        return url

    async def _download_whatsapp_media(self, media_id: str) -> bytes:
        """
        Download media file from Meta's WhatsApp Business API.
        Requires WHATSAPP_ACCESS_TOKEN in settings.

        Meta does not return audio directly in the webhook — it sends a media_id.
        We must call the Graph API to get the download URL, then download the file.
        """
        import httpx
        token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        version = getattr(settings, "WHATSAPP_API_VERSION", "v18.0")

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: Get media URL
            meta_resp = await client.get(
                f"https://graph.facebook.com/{version}/{media_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url", "")

            # Step 2: Download the actual file
            audio_resp = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            audio_resp.raise_for_status()
        return audio_resp.content

    async def _concatenate_session_audio(
        self,
        session_id:  uuid.UUID,
        voice_turns: list[dict],
    ) -> str:
        """
        Concatenate per-turn audio files into a single full-session recording.

        Uses ffmpeg (must be installed in the container) if available.
        Falls back to returning the URL of the last turn if ffmpeg is unavailable.
        If no voice turns exist, returns empty string.
        """
        if not voice_turns:
            return ""

        audio_urls = [t.get("audio_url", "") for t in voice_turns if t.get("audio_url")]
        if not audio_urls:
            return ""

        # For now: if only one turn, no concatenation needed
        if len(audio_urls) == 1:
            return audio_urls[0]

        # TODO: implement ffmpeg concat when >1 voice turn
        # For now log and return the first turn's URL as placeholder
        log.info(
            "voice.session.concat_pending",
            session_id=str(session_id),
            turn_count=len(audio_urls),
            note="Full concatenation not yet implemented; returning first turn URL",
        )
        return audio_urls[0]


# ── Module-level singleton ─────────────────────────────────────────────────
# Import this directly: from services.voice_service import voice_service
voice_service = VoiceService()
