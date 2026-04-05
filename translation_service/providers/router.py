# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/router.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/router.py — Smart provider routing for translation_service.

Routing strategy (Bolt/Uber inspiration — always pick the best available):
─────────────────────────────────────────────────────────────────────────────

  AFRICAN LANGUAGES  (sw, am, so, lg, rw, om, ha, yo, ig, zu, xh, sn, ny …)
    Primary:   Google Cloud Translation  — deepest African language support,
               best Swahili model including SMS/informal register
    Secondary: Microsoft Translator     — strong Swahili + common African langs
    Fallback:  LibreTranslate           — self-hosted, zero external calls

  EUROPEAN LANGUAGES  (en, fr, de, es, it, pt, nl, pl, ru, cs, hu …)
    Primary:   DeepL                    — highest quality for European pairs
    Secondary: Google Cloud Translation
    Fallback:  Microsoft Translator

  ASIAN LANGUAGES  (zh, ja, ko, hi, th, vi, id …)
    Primary:   Google Cloud Translation
    Secondary: Microsoft Translator
    Fallback:  LibreTranslate

  ARABIC / RTL LANGUAGES  (ar, fa, ur, he …)
    Primary:   Google Cloud Translation
    Secondary: Microsoft Translator  (strong Arabic neural MT)
    Fallback:  LibreTranslate

Fallback chain:
  If the primary provider is not configured OR raises TranslationFailedError,
  the router tries the next provider in the chain automatically.
  All attempts are logged.

Override:
  Pass explicit_provider="google"|"microsoft"|"deepl"|"libretranslate"
  to bypass routing and use a specific backend.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Optional

import structlog

from core.exceptions import (
    ProviderNotConfiguredError,
    TranslationFailedError,
)
from providers.base import BaseTranslationProvider, DetectionResult, TranslationResult

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Language family classification
# ─────────────────────────────────────────────────────────────────────────────

# Languages where Google has the deepest model quality
_GOOGLE_PREFERRED = frozenset({
    # East African
    "sw", "am", "so", "om", "ti", "rw", "rn",
    # West African
    "ha", "yo", "ig", "ak", "tw", "ee",
    # Southern African
    "zu", "xh", "st", "tn", "ts", "ve", "nr", "ss",
    # Central / other African
    "sn", "ny", "ln", "kg",
    # South / Southeast Asian
    "hi", "bn", "pa", "gu", "mr", "ta", "te", "kn", "ml",
    "th", "vi", "id", "ms", "tl",
    # East Asian
    "zh", "ja", "ko",
    # RTL
    "ar", "fa", "ur",
})

# Languages where DeepL outperforms others (European pairs)
_DEEPL_PREFERRED = frozenset({
    "en", "de", "fr", "es", "it", "pt", "nl", "pl", "ru",
    "cs", "hu", "sk", "sl", "ro", "bg", "da", "sv", "fi",
    "el", "et", "lv", "lt", "tr",
})


# ─────────────────────────────────────────────────────────────────────────────
# Provider factory
# ─────────────────────────────────────────────────────────────────────────────

def _load_provider(name: str) -> Optional[BaseTranslationProvider]:
    """Instantiate a provider by name. Returns None if not configured."""
    try:
        if name == "google":
            from providers.google_translate import GoogleTranslateProvider
            p = GoogleTranslateProvider()
        elif name == "microsoft":
            from providers.microsoft import MicrosoftTranslatorProvider
            p = MicrosoftTranslatorProvider()
        elif name == "deepl":
            from providers.deepl import DeepLProvider
            p = DeepLProvider()
        elif name == "libretranslate":
            from providers.libretranslate import LibreTranslateProvider
            p = LibreTranslateProvider()
        elif name == "nllb":
            from providers.nllb import NLLBProvider
            p = NLLBProvider()
        else:
            log.warning("provider_router.unknown_provider", name=name)
            return None
        return p if p.is_configured() else None
    except Exception as exc:
        log.warning("provider_router.load_failed", name=name, error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Routing logic
# ─────────────────────────────────────────────────────────────────────────────

def _provider_chain(target_language: str) -> list[str]:
    """
    Return ordered list of provider names to try for a given target language.
    Most preferred first.
    """
    lang = target_language.lower().split("-")[0]   # "sw-TZ" → "sw"

    if lang in _GOOGLE_PREFERRED:
        return ["google", "microsoft", "libretranslate", "nllb"]

    if lang in _DEEPL_PREFERRED:
        return ["deepl", "google", "microsoft", "libretranslate", "nllb"]

    # Default: Google → Microsoft → LibreTranslate → NLLB (local)
    return ["google", "microsoft", "libretranslate", "nllb"]


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

class ProviderRouter:
    """
    Selects and calls the best available translation provider for a request.
    Automatically falls back through the chain on failure or misconfiguration.

    Usage:
        router = ProviderRouter()
        result = await router.translate("Habari", target_language="en")
    """

    async def translate(
        self,
        text:              str,
        target_language:   str,
        source_language:   Optional[str] = None,
        explicit_provider: Optional[str] = None,
    ) -> TranslationResult:
        chain = [explicit_provider] if explicit_provider else _provider_chain(target_language)
        last_error: Optional[Exception] = None

        for name in chain:
            provider = _load_provider(name)
            if provider is None:
                log.debug("provider_router.skipped", name=name, reason="not_configured")
                continue
            try:
                result = await provider.translate(text, target_language, source_language)
                if name != (chain[0] if not explicit_provider else explicit_provider):
                    log.info("provider_router.used_fallback", used=name, target=target_language)
                return result
            except TranslationFailedError as exc:
                log.warning("provider_router.provider_failed", name=name, error=str(exc))
                last_error = exc
                continue

        raise ProviderNotConfiguredError(
            f"All translation providers failed for target='{target_language}'. "
            f"Last error: {last_error}"
        )

    async def translate_batch(
        self,
        texts:             list[str],
        target_language:   str,
        source_language:   Optional[str] = None,
        explicit_provider: Optional[str] = None,
    ) -> list[TranslationResult]:
        chain      = [explicit_provider] if explicit_provider else _provider_chain(target_language)
        last_error = None

        for name in chain:
            provider = _load_provider(name)
            if provider is None:
                continue
            try:
                return await provider.translate_batch(texts, target_language, source_language)
            except TranslationFailedError as exc:
                log.warning("provider_router.batch_failed", name=name, error=str(exc))
                last_error = exc
                continue

        raise ProviderNotConfiguredError(
            f"All providers failed for batch target='{target_language}'. Last: {last_error}"
        )

    async def detect(
        self,
        text:              str,
        explicit_provider: Optional[str] = None,
    ) -> DetectionResult:
        """
        Provider-side detection (higher accuracy than local langdetect for short texts).
        Tries Microsoft first (strong multilingual detection), then Google, then LibreTranslate.
        """
        chain      = [explicit_provider] if explicit_provider else ["microsoft", "google", "libretranslate"]
        last_error = None

        for name in chain:
            provider = _load_provider(name)
            if provider is None or not hasattr(provider, "detect"):
                continue
            try:
                return await provider.detect(text)   # type: ignore[attr-defined]
            except TranslationFailedError as exc:
                log.warning("provider_router.detect_failed", name=name, error=str(exc))
                last_error = exc
                continue

        raise ProviderNotConfiguredError(
            f"All providers failed for detection. Last: {last_error}"
        )
