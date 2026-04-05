# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/google_translate.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/google_translate.py — Google Cloud Translation API v3.

Requires:
  · GOOGLE_PROJECT_ID
  · GOOGLE_APPLICATION_CREDENTIALS  (path to JSON key or JSON content string)

Tanzania context: Google Translate has strong Swahili support, including
recognition of common regional expressions and SMS shorthand.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)


class GoogleTranslateProvider(BaseTranslationProvider):

    @property
    def name(self) -> str:
        return "google"

    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_PROJECT_ID and settings.GOOGLE_APPLICATION_CREDENTIALS)

    def _get_client(self):
        """Lazy-initialise the Google Translate client."""
        try:
            from google.cloud import translate_v3 as translate  # type: ignore
        except ImportError:
            raise TranslationFailedError(
                "google-cloud-translate package not installed.",
                error_code="PROVIDER_IMPORT_ERROR",
            )

        creds_value = settings.GOOGLE_APPLICATION_CREDENTIALS
        if creds_value and not os.path.isfile(creds_value):
            # Treat as JSON string — write to a temp file
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            tmp.write(creds_value)
            tmp.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

        return translate.TranslationServiceClient()

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._translate_sync, text, target_language, source_language
        )

    def _translate_sync(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str],
    ) -> TranslationResult:
        try:
            client  = self._get_client()
            parent  = f"projects/{settings.GOOGLE_PROJECT_ID}/locations/global"
            request = {
                "parent":              parent,
                "contents":            [text],
                "mime_type":           "text/plain",
                "target_language_code": target_language,
            }
            if source_language:
                request["source_language_code"] = source_language

            response     = client.translate_text(request=request)
            translation  = response.translations[0]
            detected_src = (
                translation.detected_language_code
                if not source_language
                else source_language
            )
            return TranslationResult(
                translated_text=translation.translated_text,
                source_language=detected_src,
                provider=self.name,
            )
        except Exception as exc:
            log.error("google_translate.error", error=str(exc))
            raise TranslationFailedError(f"Google Translate error: {exc}")

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._translate_batch_sync, texts, target_language, source_language
        )

    def _translate_batch_sync(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str],
    ) -> list[TranslationResult]:
        try:
            client = self._get_client()
            parent = f"projects/{settings.GOOGLE_PROJECT_ID}/locations/global"
            request = {
                "parent":               parent,
                "contents":             texts,
                "mime_type":            "text/plain",
                "target_language_code": target_language,
            }
            if source_language:
                request["source_language_code"] = source_language

            response = client.translate_text(request=request)
            results  = []
            for t in response.translations:
                detected = t.detected_language_code if not source_language else source_language
                results.append(TranslationResult(
                    translated_text=t.translated_text,
                    source_language=detected,
                    provider=self.name,
                ))
            return results
        except Exception as exc:
            log.error("google_translate.batch_error", error=str(exc))
            raise TranslationFailedError(f"Google Translate batch error: {exc}")
