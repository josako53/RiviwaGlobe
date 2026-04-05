# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/deepl.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/deepl.py — DeepL Translation API provider.

Requires:
  · DEEPL_API_KEY
  · DEEPL_FREE_TIER  (True → uses api-free.deepl.com endpoint)

Note: DeepL's Swahili support is limited. Recommended as fallback for
European languages (English, French, German) when Google is unavailable.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)

# DeepL uses different language codes — map BCP-47 → DeepL
_DEEPL_CODE_MAP: dict[str, str] = {
    "en": "EN",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
    "pt": "PT",
    "it": "IT",
    "nl": "NL",
    "pl": "PL",
    "ru": "RU",
    "ja": "JA",
    "zh": "ZH",
    "ar": "AR",
}


class DeepLProvider(BaseTranslationProvider):

    @property
    def name(self) -> str:
        return "deepl"

    def is_configured(self) -> bool:
        return bool(settings.DEEPL_API_KEY)

    def _to_deepl_code(self, bcp47: str) -> str:
        return _DEEPL_CODE_MAP.get(bcp47.lower(), bcp47.upper())

    def _get_translator(self):
        try:
            import deepl  # type: ignore
        except ImportError:
            raise TranslationFailedError("deepl package not installed.", error_code="PROVIDER_IMPORT_ERROR")
        return deepl.Translator(settings.DEEPL_API_KEY)

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        def _run():
            translator    = self._get_translator()
            target        = self._to_deepl_code(target_language)
            source        = self._to_deepl_code(source_language) if source_language else None
            try:
                result = translator.translate_text(text, target_lang=target, source_lang=source)
                return TranslationResult(
                    translated_text=result.text,
                    source_language=result.detected_source_lang.lower(),
                    provider=self.name,
                )
            except Exception as exc:
                log.error("deepl.translate_error", error=str(exc))
                raise TranslationFailedError(f"DeepL error: {exc}")

        return await asyncio.get_event_loop().run_in_executor(None, _run)

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        def _run():
            translator = self._get_translator()
            target     = self._to_deepl_code(target_language)
            source     = self._to_deepl_code(source_language) if source_language else None
            try:
                results = translator.translate_text(texts, target_lang=target, source_lang=source)
                return [
                    TranslationResult(
                        translated_text=r.text,
                        source_language=r.detected_source_lang.lower(),
                        provider=self.name,
                    )
                    for r in results
                ]
            except Exception as exc:
                log.error("deepl.batch_error", error=str(exc))
                raise TranslationFailedError(f"DeepL batch error: {exc}")

        return await asyncio.get_event_loop().run_in_executor(None, _run)
