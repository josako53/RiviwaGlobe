"""services/stt_service.py — Speech-to-text for voice notes (WhatsApp audio)."""
from __future__ import annotations
from typing import Optional
import httpx
import structlog
from core.config import settings

log = structlog.get_logger(__name__)


class STTService:
    """
    Transcribes audio from WhatsApp voice notes.
    Uses OpenAI Whisper API as primary; falls back to returning empty string on failure.
    """

    async def download_whatsapp_audio(self, media_id: str) -> Optional[bytes]:
        """Download audio bytes from Meta WhatsApp Cloud API."""
        if not settings.WHATSAPP_ACCESS_TOKEN:
            log.warning("stt.whatsapp_token_missing")
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: resolve media URL
                r = await client.get(
                    f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}",
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                )
                r.raise_for_status()
                url = r.json().get("url")
                if not url:
                    return None
                # Step 2: download the audio
                r2 = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                )
                r2.raise_for_status()
                return r2.content
        except Exception as exc:
            log.error("stt.download_failed", media_id=media_id, error=str(exc))
            return None

    async def transcribe(self, audio_bytes: bytes, language_hint: str = "sw") -> Optional[str]:
        """
        Transcribe audio bytes using OpenAI Whisper API.
        Returns the transcript text, or None on failure.
        """
        if not settings.OPENAI_API_KEY:
            log.warning("stt.openai_key_missing")
            return None
        # Map Riviwa language codes → Whisper language codes
        lang_map = {"sw": "sw", "en": "en"}
        whisper_lang = lang_map.get(language_hint, "sw")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                    data={
                        "model": "whisper-1",
                        "language": whisper_lang,
                        "response_format": "text",
                    },
                )
                r.raise_for_status()
                transcript = r.text.strip()
                log.info("stt.transcribed", length=len(transcript), language=whisper_lang)
                return transcript
        except Exception as exc:
            log.error("stt.transcribe_failed", error=str(exc))
            return None

    async def process_whatsapp_voice(self, media_id: str, language_hint: str = "sw") -> Optional[str]:
        """Download and transcribe a WhatsApp voice note. Returns transcript or None."""
        audio = await self.download_whatsapp_audio(media_id)
        if not audio:
            return None
        return await self.transcribe(audio, language_hint)
