# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/microsoft.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/microsoft.py — Microsoft Azure Cognitive Services Translator v3.

Requires:
  · MICROSOFT_TRANSLATOR_KEY     — Azure subscription key
  · MICROSOFT_TRANSLATOR_REGION  — Azure region (e.g. "eastus")

Why Microsoft as secondary/fallback:
  · Broad language coverage (100+ languages)
  · Strong Swahili support with better regional variant awareness than DeepL
  · Neural MT engine comparable in quality to Google for most African languages
  · Free tier: 2M chars/month (F0); easy upgrade path

API docs: https://learn.microsoft.com/en-us/azure/ai-services/translator/
"""
from __future__ import annotations

from typing import Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, DetectionResult, TranslationResult

log = structlog.get_logger(__name__)

_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
_API_VER  = "3.0"


class MicrosoftTranslatorProvider(BaseTranslationProvider):

    @property
    def name(self) -> str:
        return "microsoft"

    def is_configured(self) -> bool:
        return bool(
            settings.MICROSOFT_TRANSLATOR_KEY
            and settings.MICROSOFT_TRANSLATOR_REGION
        )

    def _headers(self) -> dict:
        return {
            "Ocp-Apim-Subscription-Key":    settings.MICROSOFT_TRANSLATOR_KEY,
            "Ocp-Apim-Subscription-Region": settings.MICROSOFT_TRANSLATOR_REGION,
            "Content-Type":                 "application/json",
        }

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        url    = f"{_ENDPOINT}/translate"
        params = {"api-version": _API_VER, "to": target_language}
        if source_language:
            params["from"] = source_language

        body = [{"text": text}]

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(url, headers=self._headers(), params=params, json=body)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error("microsoft.translate_error", status=exc.response.status_code, body=exc.response.text)
                raise TranslationFailedError(f"Microsoft Translator HTTP {exc.response.status_code}")
            except httpx.RequestError as exc:
                log.error("microsoft.request_error", error=str(exc))
                raise TranslationFailedError(f"Microsoft Translator connection error: {exc}")

        data       = resp.json()
        item       = data[0]
        translated = item["translations"][0]["text"]
        detected   = source_language or item.get("detectedLanguage", {}).get("language", "unknown")
        return TranslationResult(
            translated_text=translated,
            source_language=detected,
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        """
        Microsoft Translator supports up to 100 items per batch request.
        We send all texts in one HTTP call.
        """
        url    = f"{_ENDPOINT}/translate"
        params = {"api-version": _API_VER, "to": target_language}
        if source_language:
            params["from"] = source_language

        body = [{"text": t} for t in texts]

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, headers=self._headers(), params=params, json=body)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error("microsoft.batch_error", status=exc.response.status_code)
                raise TranslationFailedError(f"Microsoft Translator batch HTTP {exc.response.status_code}")
            except httpx.RequestError as exc:
                raise TranslationFailedError(f"Microsoft Translator connection error: {exc}")

        results = []
        for item in resp.json():
            translated = item["translations"][0]["text"]
            detected   = source_language or item.get("detectedLanguage", {}).get("language", "unknown")
            results.append(TranslationResult(
                translated_text=translated,
                source_language=detected,
                provider=self.name,
            ))
        return results

    async def detect(self, text: str) -> DetectionResult:
        """
        Use Microsoft's dedicated detect endpoint.
        Returns language code + confidence score.
        """
        url  = f"{_ENDPOINT}/detect"
        body = [{"text": text}]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._headers(),
                    params={"api-version": _API_VER},
                    json=body,
                )
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                raise TranslationFailedError(f"Microsoft detect error: {exc}")

        data  = resp.json()[0]
        lang  = data.get("language", "unknown")
        score = data.get("score", 0.0)
        alternatives = [
            {"language": a["language"], "confidence": round(a["score"], 4)}
            for a in data.get("alternatives", [])
        ]
        return DetectionResult(
            detected_language=lang,
            confidence=round(score, 4),
            provider=self.name,
            alternatives=alternatives,
        )
