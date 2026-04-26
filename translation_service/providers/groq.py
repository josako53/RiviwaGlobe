"""
providers/groq.py — Groq LLM translation provider.

Uses Groq's OpenAI-compatible chat API with llama-3.3-70b-versatile for
translation. Sub-second latency, free tier, supports 100+ languages
including Swahili, Hausa, Amharic, Yoruba, Zulu, and all major languages.

Set GROQ_API_KEY in .env to activate this provider.
Used automatically as the primary fallback when no dedicated translation
API (Google, DeepL, Microsoft, LibreTranslate) is configured.
"""
from __future__ import annotations

import re
from typing import Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)

_API_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a precise translation engine. "
    "Translate the user's text to {target_language}. "
    "Rules:\n"
    "1. Return ONLY the translated text — no explanations, no quotes, no labels.\n"
    "2. Preserve formatting, punctuation, and line breaks exactly.\n"
    "3. If the text is already in {target_language}, return it unchanged.\n"
    "4. For proper nouns (names, places) keep the original form unless a standard "
    "translation exists in the target language."
)

# BCP-47 → full language name for clear LLM instruction
_LANG_NAMES: dict[str, str] = {
    "sw": "Swahili", "en": "English", "fr": "French", "ar": "Arabic",
    "pt": "Portuguese", "es": "Spanish", "de": "German", "zh": "Chinese",
    "ja": "Japanese", "hi": "Hindi", "am": "Amharic", "ha": "Hausa",
    "yo": "Yoruba", "so": "Somali", "af": "Afrikaans", "zu": "Zulu",
    "it": "Italian", "ru": "Russian", "nl": "Dutch", "ko": "Korean",
    "tr": "Turkish", "fa": "Persian", "ur": "Urdu", "bn": "Bengali",
    "pl": "Polish", "vi": "Vietnamese", "th": "Thai", "id": "Indonesian",
    "ms": "Malay",
}


def _lang_name(code: str) -> str:
    return _LANG_NAMES.get(code.lower().split("-")[0], code)


class GroqTranslationProvider(BaseTranslationProvider):
    """
    Translation via Groq chat completion (llama-3.3-70b-versatile).
    Accurate, fast (< 1 s for short texts), free tier generous.
    """

    @property
    def name(self) -> str:
        return "groq"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        if not self.is_configured():
            raise TranslationFailedError("Groq provider: GROQ_API_KEY not set.")

        target_name = _lang_name(target_language)
        system      = _SYSTEM_PROMPT.format(target_language=target_name)

        user_content = text
        if source_language:
            source_name  = _lang_name(source_language)
            user_content = f"[Source language: {source_name}]\n{text}"

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    _API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       settings.GROQ_TRANSLATION_MODEL,
                        "messages":    [
                            {"role": "system", "content": system},
                            {"role": "user",   "content": user_content},
                        ],
                        "temperature": 0.1,   # low temperature for deterministic translation
                        "max_tokens":  2048,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as exc:
            log.error("groq.translate_http_error",
                      status=exc.response.status_code, body=exc.response.text[:200])
            raise TranslationFailedError(
                f"Groq translation HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            )
        except Exception as exc:
            log.error("groq.translate_error", error=str(exc))
            raise TranslationFailedError(f"Groq translation failed: {exc}")

        translated = data["choices"][0]["message"]["content"].strip()
        # Strip any accidental quote wrapping the LLM may add
        if len(translated) >= 2 and translated[0] in ('"', "'") and translated[-1] == translated[0]:
            translated = translated[1:-1].strip()

        detected_source = source_language or "auto"
        log.info("groq.translated",
                 chars_in=len(text), chars_out=len(translated),
                 target=target_language, source=detected_source)
        return TranslationResult(
            translated_text=translated,
            source_language=detected_source,
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        """
        Translate a list of strings. Groq is fast enough that sequential
        calls are practical for batches up to ~20 items. For larger batches
        we concatenate with separators to reduce round trips.
        """
        if len(texts) == 1:
            return [await self.translate(texts[0], target_language, source_language)]

        # For batches ≤ 10 use separator trick: translate all in one call
        if len(texts) <= 10:
            sep      = "\n<<<SEP>>>\n"
            combined = sep.join(texts)
            result   = await self.translate(combined, target_language, source_language)
            parts    = result.translated_text.split("<<<SEP>>>")
            # Pad or truncate to match input length
            parts    = [p.strip() for p in parts]
            while len(parts) < len(texts):
                parts.append("")
            return [
                TranslationResult(
                    translated_text=parts[i],
                    source_language=result.source_language,
                    provider=self.name,
                )
                for i in range(len(texts))
            ]

        # For larger batches, translate sequentially
        results = []
        for text in texts:
            results.append(await self.translate(text, target_language, source_language))
        return results
