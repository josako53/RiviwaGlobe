# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/libretranslate.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/libretranslate.py — LibreTranslate self-hosted open-source provider.

Why LibreTranslate as the offline/emergency fallback:
  · 100% open source (AGPL-3.0) — no per-character billing
  · Self-hostable inside the Riviwa Docker network (no external API calls)
  · Supports 30+ languages including Swahili via Argos Translate models
  · Zero data leaves the deployment environment — GDPR / data sovereignty friendly

Production deployment:
  Add `libretranslate` container to docker-compose.yml.
  Set LIBRETRANSLATE_URL=http://libretranslate:5000 (internal Docker network).
  Optionally set LIBRETRANSLATE_API_KEY if you have auth enabled on the instance.

Docker image: libretranslate/libretranslate:latest
Argos models auto-download on first startup (~200 MB per language pair).

API docs: https://libretranslate.com/docs/
"""
from __future__ import annotations

from typing import Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, DetectionResult, TranslationResult

log = structlog.get_logger(__name__)


class LibreTranslateProvider(BaseTranslationProvider):

    @property
    def name(self) -> str:
        return "libretranslate"

    def is_configured(self) -> bool:
        return bool(settings.LIBRE_TRANSLATE_URL)

    def _base_url(self) -> str:
        return settings.LIBRE_TRANSLATE_URL.rstrip("/")

    def _api_key_payload(self) -> dict:
        """Conditionally include api_key if configured."""
        if settings.LIBRE_TRANSLATE_API_KEY:
            return {"api_key": settings.LIBRE_TRANSLATE_API_KEY}
        return {}

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        url     = f"{self._base_url()}/translate"
        payload = {
            "q":      text,
            "source": source_language or "auto",
            "target": target_language,
            "format": "text",
            **self._api_key_payload(),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text
                log.error("libretranslate.translate_error", status=exc.response.status_code, body=body)
                raise TranslationFailedError(
                    f"LibreTranslate HTTP {exc.response.status_code}: {body[:200]}"
                )
            except httpx.RequestError as exc:
                log.error("libretranslate.connection_error", error=str(exc), url=url)
                raise TranslationFailedError(
                    f"LibreTranslate unreachable at {self._base_url()}. "
                    "Check LIBRETRANSLATE_URL and ensure the container is running."
                )

        data             = resp.json()
        translated_text  = data.get("translatedText", "")
        detected_source  = data.get("detectedLanguage", {}).get("language", source_language or "auto")

        if not translated_text:
            raise TranslationFailedError("LibreTranslate returned an empty translation.")

        return TranslationResult(
            translated_text=translated_text,
            source_language=detected_source if detected_source != "auto" else (source_language or "unknown"),
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        """
        LibreTranslate v1.3+ supports batch translation via array input.
        Falls back to sequential single-text calls on older instances.
        """
        url     = f"{self._base_url()}/translate"
        payload = {
            "q":      texts,      # list triggers batch mode
            "source": source_language or "auto",
            "target": target_language,
            "format": "text",
            **self._api_key_payload(),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 400:
                    # Older LibreTranslate that doesn't support batch — fall back
                    return await self._translate_sequential(texts, target_language, source_language)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TranslationFailedError(f"LibreTranslate batch HTTP {exc.response.status_code}")
            except httpx.RequestError as exc:
                raise TranslationFailedError(f"LibreTranslate connection error: {exc}")

        data = resp.json()
        # Batch response: {"translatedText": ["t1", "t2", ...]}
        translations = data.get("translatedText", [])
        detected_src = data.get("detectedLanguage", {}).get("language", source_language or "unknown")

        return [
            TranslationResult(
                translated_text=t,
                source_language=detected_src,
                provider=self.name,
            )
            for t in translations
        ]

    async def _translate_sequential(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str],
    ) -> list[TranslationResult]:
        """Sequential fallback for LibreTranslate instances without batch support."""
        results = []
        for text in texts:
            result = await self.translate(text, target_language, source_language)
            results.append(result)
        return results

    async def detect(self, text: str) -> DetectionResult:
        """LibreTranslate /detect endpoint — returns scored language list."""
        url     = f"{self._base_url()}/detect"
        payload = {"q": text, **self._api_key_payload()}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                raise TranslationFailedError(f"LibreTranslate detect error: {exc}")

        items = resp.json()   # [{"language": "sw", "confidence": 0.87}, ...]
        if not items:
            raise TranslationFailedError("LibreTranslate detect returned no results.")

        best  = items[0]
        return DetectionResult(
            detected_language=best["language"],
            confidence=round(best.get("confidence", 0.0), 4),
            provider=self.name,
            alternatives=[
                {"language": i["language"], "confidence": round(i.get("confidence", 0.0), 4)}
                for i in items[1:]
            ],
        )
