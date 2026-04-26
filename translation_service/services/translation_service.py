# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  services/translation_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/translation_service.py — Translation orchestration with Redis caching.

Provider selection:
  TRANSLATION_PROVIDER=google  → GoogleTranslateProvider
  TRANSLATION_PROVIDER=deepl   → DeepLProvider
  Any unconfigured provider raises ProviderNotConfiguredError.

Caching:
  Translated strings are cached in Redis for TRANSLATION_CACHE_TTL seconds
  (default 24 h). Cache key: sha256(text + target + source).
  Same text in the same language pair is never sent to the provider twice.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

import structlog

from core.config import settings
from events.producer import get_producer
from core.exceptions import ProviderNotConfiguredError, TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)


def _get_provider() -> BaseTranslationProvider:
    provider = settings.TRANSLATION_PROVIDER.lower()
    if provider == "google":
        from providers.google_translate import GoogleTranslateProvider
        p = GoogleTranslateProvider()
    elif provider == "deepl":
        from providers.deepl import DeepLProvider
        p = DeepLProvider()
    elif provider == "nllb":
        from providers.nllb import NLLBProvider
        p = NLLBProvider()
    elif provider == "libretranslate":
        from providers.libretranslate import LibreTranslateProvider
        p = LibreTranslateProvider()
    elif provider == "microsoft":
        from providers.microsoft import MicrosoftTranslatorProvider
        p = MicrosoftTranslatorProvider()
    else:
        raise ProviderNotConfiguredError(
            f"Unknown TRANSLATION_PROVIDER: '{provider}'. "
            f"Must be: google | deepl | nllb | libretranslate | microsoft."
        )
    if not p.is_configured():
        raise ProviderNotConfiguredError(
            f"Translation provider '{provider}' is not configured. "
            f"Check the required environment variables."
        )
    return p


def _get_named_provider(name: str) -> BaseTranslationProvider:
    """Return a specific provider by name, falling back to default if not configured."""
    name = name.lower()
    try:
        if name == "google":
            from providers.google_translate import GoogleTranslateProvider
            p = GoogleTranslateProvider()
        elif name == "deepl":
            from providers.deepl import DeepLProvider
            p = DeepLProvider()
        elif name == "nllb":
            from providers.nllb import NLLBProvider
            p = NLLBProvider()
        elif name == "libretranslate":
            from providers.libretranslate import LibreTranslateProvider
            p = LibreTranslateProvider()
        elif name == "microsoft":
            from providers.microsoft import MicrosoftTranslatorProvider
            p = MicrosoftTranslatorProvider()
        else:
            return _get_provider()
        if p.is_configured():
            return p
    except Exception:
        pass
    return _get_provider()  # fallback to default


def _cache_key(text: str, target: str, source: Optional[str]) -> str:
    raw = f"{text}|{target}|{source or 'auto'}"
    return "trans:" + hashlib.sha256(raw.encode()).hexdigest()


def _get_redis():
    try:
        import redis.asyncio as aioredis  # type: ignore
        return aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


class TranslationOrchestrator:
    """
    Wraps provider calls with:
      · Redis result caching
      · Automatic provider selection
      · Structured logging for all translate calls
    """

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
        provider:        Optional[str] = None,
    ) -> dict:
        """Returns dict matching TranslateResponse schema."""
        cache_key = _cache_key(text, target_language, source_language)
        redis     = _get_redis()

        # Cache read
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    data["cached"] = True
                    return data
            except Exception:
                pass  # Redis unavailable — proceed without cache

        prov   = _get_named_provider(provider) if provider else _get_provider()
        result = await prov.translate(text, target_language, source_language)

        response = {
            "translated_text": result.translated_text,
            "source_language": result.source_language,
            "target_language": target_language,
            "provider":        result.provider,
            "cached":          False,
        }

        # Cache write
        if redis:
            try:
                await redis.setex(
                    cache_key,
                    settings.TRANSLATION_CACHE_TTL,
                    json.dumps(response),
                )
            except Exception:
                pass

        log.info(
            "translation.completed",
            provider=result.provider,
            source=result.source_language,
            target=target_language,
            chars=len(text),
        )

        # Publish translation.completed event (cache miss only — actual provider call)
        try:
            producer = await get_producer()
            await producer.translation_completed(
                source_language = result.source_language,
                target_language = target_language,
                provider        = result.provider,
                char_count      = len(text),
            )
        except Exception as _exc:
            log.warning("translation.event_publish_failed", error=str(_exc))

        return response

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
        provider:        Optional[str] = None,
    ) -> list[dict]:
        """Returns list of dicts matching TranslateResponse schema."""
        results = []
        redis   = _get_redis()

        uncached_indices: list[int] = []
        uncached_texts:   list[str] = []

        # Check cache for each text
        for i, text in enumerate(texts):
            key    = _cache_key(text, target_language, source_language)
            cached = None
            if redis:
                try:
                    raw = await redis.get(key)
                    if raw:
                        cached = json.loads(raw)
                        cached["cached"] = True
                except Exception:
                    pass
            if cached:
                results.append((i, cached))
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Translate uncached texts in one provider call
        if uncached_texts:
            _prov          = _get_named_provider(provider) if provider else _get_provider()
            provider_results: list[TranslationResult] = await _prov.translate_batch(
                uncached_texts, target_language, source_language
            )
            for idx, (orig_i, pr) in enumerate(zip(uncached_indices, provider_results)):
                response = {
                    "translated_text": pr.translated_text,
                    "source_language": pr.source_language,
                    "target_language": target_language,
                    "provider":        pr.provider,
                    "cached":          False,
                }
                results.append((orig_i, response))
                if redis:
                    try:
                        key = _cache_key(uncached_texts[idx], target_language, source_language)
                        await redis.setex(key, settings.TRANSLATION_CACHE_TTL, json.dumps(response))
                    except Exception:
                        pass

        # Re-sort by original index
        results.sort(key=lambda x: x[0])
        return [r for _, r in results]
