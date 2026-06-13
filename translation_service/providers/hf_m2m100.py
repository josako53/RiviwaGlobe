"""
providers/hf_m2m100.py — HuggingFace Inference API provider for M2M-100.

facebook/m2m100_418M  — faster, free tier friendly (default)
facebook/m2m100_1.2B  — higher quality (set HF_M2M100_MODEL in .env)

Cold-start behaviour (free HF tier):
  The model unloads after ~10 minutes of inactivity and takes 10–20 s to reload.
  On a 503 the API returns {"error": "...", "estimated_time": N}. We wait N seconds
  (capped at 30) then retry once. If still 503, raise TranslationFailedError so
  the router falls back to Groq automatically.

Set HF_TOKEN in .env to activate this provider.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)

_HF_BASE = "https://api-inference.huggingface.co/models"

# M2M-100 supports ISO 639-1 codes. A handful of common ones need remapping
# from BCP-47 variants that other providers accept.
_CODE_MAP: dict[str, str] = {
    "zh-cn": "zh", "zh-tw": "zh", "zh-hk": "zh",
    "pt-br": "pt", "pt-pt": "pt",
    "fr-ca": "fr",
    "es-mx": "es", "es-419": "es",
    "ar-sa": "ar", "ar-eg": "ar",
}

# Languages M2M-100 covers well — used by the router to prefer this provider.
HF_M2M_SUPPORTED = frozenset({
    "sw", "en", "fr", "ar", "am", "so", "ha", "yo", "ig",
    "zu", "xh", "ny", "rw", "lg", "sn", "af",
    "de", "es", "pt", "it", "nl", "pl", "ru", "cs",
    "zh", "ja", "ko", "hi", "bn", "ur", "vi", "id", "ms", "tr",
})


def _normalize(code: str) -> str:
    c = code.lower().split("-")[0] if "-" not in _CODE_MAP else _CODE_MAP.get(code.lower(), code.lower().split("-")[0])
    return _CODE_MAP.get(code.lower(), c)


class HFM2M100Provider(BaseTranslationProvider):
    """
    Translation via HuggingFace Serverless Inference API (M2M-100).
    Primary provider for African and common world languages.
    Falls back to Groq automatically on 503 cold-start timeout.
    """

    @property
    def name(self) -> str:
        return "hf_m2m100"

    @property
    def _api_url(self) -> str:
        return f"{_HF_BASE}/{settings.HF_M2M100_MODEL}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.HF_TOKEN}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(settings.HF_TOKEN)

    async def _call(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str,
        client: httpx.AsyncClient,
        _retry: bool = True,
    ) -> str:
        """Single translation call with one cold-start retry."""
        payload = {
            "inputs": text,
            "parameters": {"src_lang": src_lang, "tgt_lang": tgt_lang},
        }
        r = await client.post(self._api_url, headers=self._headers, json=payload)

        if r.status_code == 503:
            if not _retry:
                raise TranslationFailedError(
                    f"HF M2M-100 still loading after wait — model={settings.HF_M2M100_MODEL}"
                )
            try:
                data = r.json()
                wait = min(float(data.get("estimated_time", 20)), 30)
            except Exception:
                wait = 20
            log.info("hf_m2m100.cold_start", wait_seconds=wait, model=settings.HF_M2M100_MODEL)
            await asyncio.sleep(wait)
            return await self._call(text, src_lang, tgt_lang, client, _retry=False)

        if r.status_code != 200:
            raise TranslationFailedError(
                f"HF M2M-100 HTTP {r.status_code}: {r.text[:200]}"
            )

        result = r.json()
        if isinstance(result, list) and result:
            return result[0].get("translation_text", "")
        if isinstance(result, dict) and "error" in result:
            raise TranslationFailedError(f"HF M2M-100 error: {result['error']}")
        raise TranslationFailedError(f"HF M2M-100 unexpected response: {str(result)[:200]}")

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        if not self.is_configured():
            raise TranslationFailedError("HF M2M-100: HF_TOKEN not set.")

        src = _normalize(source_language or settings.DEFAULT_LANGUAGE)
        tgt = _normalize(target_language)

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                translated = await self._call(text, src, tgt, client)
        except TranslationFailedError:
            raise
        except Exception as exc:
            log.error("hf_m2m100.translate_error", error=str(exc))
            raise TranslationFailedError(f"HF M2M-100 failed: {exc}")

        log.info("hf_m2m100.translated",
                 chars_in=len(text), chars_out=len(translated),
                 src=src, tgt=tgt)
        return TranslationResult(
            translated_text=translated,
            source_language=src,
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        src = _normalize(source_language or settings.DEFAULT_LANGUAGE)
        tgt = _normalize(target_language)
        results = []
        async with httpx.AsyncClient(timeout=45.0) as client:
            for text in texts:
                try:
                    translated = await self._call(text, src, tgt, client)
                    results.append(TranslationResult(
                        translated_text=translated,
                        source_language=src,
                        provider=self.name,
                    ))
                except TranslationFailedError as exc:
                    log.warning("hf_m2m100.batch_item_failed", error=str(exc))
                    raise
        return results

    async def warm_up(self) -> None:
        """Send a minimal request to keep the HF model loaded."""
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                await self._call("Hello", "en", "sw", client, _retry=False)
            log.debug("hf_m2m100.keep_warm_ok", model=settings.HF_M2M100_MODEL)
        except Exception as exc:
            log.debug("hf_m2m100.keep_warm_failed", error=str(exc))
