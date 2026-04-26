"""services/stt_service.py — Speech-to-text for voice notes."""
from __future__ import annotations
from typing import Optional, Tuple
import httpx
import structlog
from core.config import settings

log = structlog.get_logger(__name__)

# Map MIME type → file extension for Whisper API upload
_MIME_TO_EXT: dict[str, str] = {
    "audio/webm":      "webm",
    "audio/ogg":       "ogg",
    "audio/mpeg":      "mp3",
    "audio/mp3":       "mp3",
    "audio/wav":       "wav",
    "audio/wave":      "wav",
    "audio/x-wav":     "wav",
    "audio/mp4":       "mp4",
    "audio/m4a":       "m4a",
    "audio/aac":       "aac",
    "audio/amr":       "amr",
    "audio/opus":      "opus",
    "video/webm":      "webm",
}

# Whisper returns full language names — map back to BCP-47
_WHISPER_LANG_TO_BCP47: dict[str, str] = {
    "swahili":     "sw",
    "english":     "en",
    "french":      "fr",
    "arabic":      "ar",
    "portuguese":  "pt",
    "spanish":     "es",
    "german":      "de",
    "chinese":     "zh",
    "japanese":    "ja",
    "hindi":       "hi",
    "amharic":     "am",
    "hausa":       "ha",
    "yoruba":      "yo",
    "somali":      "so",
    "afrikaans":   "af",
}


class STTService:
    """
    Speech-to-text using OpenAI Whisper API (primary).
    Supports audio uploaded directly (multipart) or downloaded from WhatsApp/Twilio.
    """

    # ── Core transcription ────────────────────────────────────────────────────

    async def transcribe(
        self,
        audio_bytes: bytes,
        language_hint: Optional[str] = None,
        content_type: str = "audio/ogg",
    ) -> Optional[str]:
        """Transcribe audio bytes. Returns plain transcript text or None."""
        result = await self.transcribe_with_detection(audio_bytes, content_type, language_hint)
        return result[0] if result else None

    async def transcribe_with_detection(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/webm",
        language_hint: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """
        Transcribe audio and auto-detect language in a single Whisper call.

        Provider priority:
          1. OpenAI Whisper API  (if OPENAI_API_KEY is set)
          2. Groq Whisper API    (if GROQ_API_KEY is set — whisper-large-v3-turbo,
                                  same verbose_json format, 10-100x faster, free tier)

        Returns: (transcript, bcp47_language_code, confidence)
        """
        # Resolve provider
        api_key, base_url, model = self._resolve_stt_provider()
        if not api_key:
            log.warning("stt.no_provider_configured",
                        hint="Set OPENAI_API_KEY or GROQ_API_KEY in .env")
            return ("", "sw", 0.0)

        ext      = _MIME_TO_EXT.get(content_type.split(";")[0].strip(), "webm")
        filename = f"audio.{ext}"

        form_data: dict = {
            "model":           model,
            "response_format": "verbose_json",
        }
        if language_hint:
            form_data["language"] = language_hint

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (filename, audio_bytes, content_type)},
                    data=form_data,
                )
                r.raise_for_status()
                data = r.json()

            transcript   = data.get("text", "").strip()
            whisper_lang = data.get("language", "swahili").lower()
            bcp47        = _WHISPER_LANG_TO_BCP47.get(whisper_lang, whisper_lang[:2])

            # avg_logprob proxy: -0.0 = perfect, -1.0 = noisy; map to [0, 1]
            segments    = data.get("segments", [])
            avg_logprob = segments[0].get("avg_logprob", -0.5) if segments else -0.5
            confidence  = max(0.0, min(1.0, 1.0 + avg_logprob))

            log.info("stt.transcribed_with_detection",
                     provider=base_url.split("//")[1].split("/")[0],
                     lang=bcp47, confidence=round(confidence, 2),
                     chars=len(transcript))
            return (transcript, bcp47, confidence)

        except Exception as exc:
            log.error("stt.transcribe_failed", error=str(exc))
            return ("", "sw", 0.0)

    def _resolve_stt_provider(self) -> tuple[str, str, str]:
        """
        Return (api_key, base_url, model_name) for the first configured STT provider.
        Priority: OpenAI → Groq (whisper-large-v3-turbo).
        """
        if settings.OPENAI_API_KEY:
            return (
                settings.OPENAI_API_KEY,
                "https://api.openai.com/v1",
                "whisper-1",
            )
        if settings.GROQ_API_KEY:
            return (
                settings.GROQ_API_KEY,
                "https://api.groq.com/openai/v1",
                "whisper-large-v3-turbo",   # fastest, multilingual, free tier
            )
        return ("", "", "")

    # ── Source-specific download helpers ─────────────────────────────────────

    async def download_whatsapp_audio(self, media_id: str) -> Optional[bytes]:
        """Download audio bytes from Meta WhatsApp Cloud API."""
        if not settings.WHATSAPP_ACCESS_TOKEN:
            log.warning("stt.whatsapp_token_missing")
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}",
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                )
                r.raise_for_status()
                url = r.json().get("url")
                if not url:
                    return None
                r2 = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                )
                r2.raise_for_status()
                return r2.content
        except Exception as exc:
            log.error("stt.whatsapp_download_failed", media_id=media_id, error=str(exc))
            return None

    async def download_twilio_recording(self, recording_url: str) -> Optional[bytes]:
        """Download a Twilio call recording (MP3) using Basic Auth."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            log.warning("stt.twilio_credentials_missing")
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    recording_url,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                )
                r.raise_for_status()
                return r.content
        except Exception as exc:
            log.error("stt.twilio_download_failed", url=recording_url, error=str(exc))
            return None

    async def process_whatsapp_voice(self, media_id: str, language_hint: str = "sw") -> Optional[str]:
        """Download and transcribe a WhatsApp voice note. Returns transcript or None."""
        audio = await self.download_whatsapp_audio(media_id)
        if not audio:
            return None
        return await self.transcribe(audio, language_hint=language_hint, content_type="audio/ogg")
