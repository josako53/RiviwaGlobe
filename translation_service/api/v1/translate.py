# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  api/v1/translate.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/translate.py — Translation and language detection endpoints.

Routes
──────
  POST /translate           Translate a single text
  POST /translate/batch     Translate multiple texts in one call
  POST /detect              Detect the language of a text
  GET  /languages           List all supported language codes
  GET  /health              Provider health check
"""
from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.dependencies import DbDep, ServiceKeyDep
from core.exceptions import (
    DetectionFailedError,
    LanguageNotSupportedError,
    ProviderNotConfiguredError,
    TranslationFailedError,
)
from providers.nllb import BCP47_TO_FLORES
from services.detection_service import DetectionService
from services.translation_service import TranslationOrchestrator

log    = structlog.get_logger(__name__)
router = APIRouter(tags=["Translation"])


# ─────────────────────────────────────────────────────────────────────────────
# Request / response schemas
# ─────────────────────────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text:            str           = Field(min_length=1, max_length=10_000,
                                          description="Text to translate")
    target_language: str           = Field(description="BCP-47 target code, e.g. 'en', 'sw'")
    source_language: Optional[str] = Field(default=None,
                                          description="BCP-47 source code. Omit to auto-detect.")
    provider:        Optional[str] = Field(default=None,
                                          description="Force a specific provider: google | deepl | nllb | microsoft | libretranslate")


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    provider:        str
    cached:          bool


class BatchTranslateRequest(BaseModel):
    texts:           list[str]     = Field(min_length=1, max_length=50,
                                          description="List of texts to translate (max 50)")
    target_language: str           = Field(description="BCP-47 target code")
    source_language: Optional[str] = Field(default=None)
    provider:        Optional[str] = Field(default=None)


class BatchTranslateResponse(BaseModel):
    results: list[TranslateResponse]
    total:   int


class DetectRequest(BaseModel):
    text: str = Field(min_length=5, max_length=5_000,
                      description="Text to detect language from")


class DetectResponse(BaseModel):
    detected_language: str
    confidence:        float
    alternatives:      list[dict]


class SupportedLanguage(BaseModel):
    code:       str   # BCP-47
    flores_code: str  # FLORES-200 (NLLB internal)


class SupportedLanguagesResponse(BaseModel):
    languages: list[SupportedLanguage]
    total:     int


class HealthResponse(BaseModel):
    status:    str
    providers: dict[str, bool]
    nllb_loaded: bool


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _orchestrator() -> TranslationOrchestrator:
    return TranslationOrchestrator()


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/translate",
    response_model=TranslateResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate a single text",
    description=(
        "Translates text to the target language using the configured provider chain.\n\n"
        "Provider resolution order (when no explicit provider is given):\n"
        "- **African / Asian languages** → Google → Microsoft → NLLB (local)\n"
        "- **European languages**       → DeepL → Google → NLLB (local)\n\n"
        "NLLB-200 is always available as the last-resort local fallback with "
        "zero external API calls."
    ),
)
async def translate(body: TranslateRequest) -> TranslateResponse:
    svc = _orchestrator()
    try:
        result = await svc.translate(
            text=body.text,
            target_language=body.target_language,
            source_language=body.source_language,
            explicit_provider=body.provider,
        )
        return TranslateResponse(**result)
    except (TranslationFailedError, ProviderNotConfiguredError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/translate/batch",
    response_model=BatchTranslateResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate multiple texts in one call",
    description="Accepts up to 50 texts and returns a result for each. Cache is checked per-text.",
)
async def translate_batch(body: BatchTranslateRequest) -> BatchTranslateResponse:
    if len(body.texts) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 50 texts per batch request.",
        )
    svc = _orchestrator()
    try:
        results = await svc.translate_batch(
            texts=body.texts,
            target_language=body.target_language,
            source_language=body.source_language,
            explicit_provider=body.provider,
        )
        return BatchTranslateResponse(
            results=[TranslateResponse(**r) for r in results],
            total=len(results),
        )
    except (TranslationFailedError, ProviderNotConfiguredError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/detect",
    response_model=DetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect the language of a text",
    description=(
        "Uses langdetect + langid ensemble locally. "
        "Requires at least 20 characters for reliable results."
    ),
)
async def detect_language(body: DetectRequest, db: DbDep) -> DetectResponse:
    from repositories.language_repository import LanguageRepository
    svc = DetectionService(repo=LanguageRepository(db))
    try:
        lang, confidence, alternatives = svc._run_langdetect(body.text)
        return DetectResponse(
            detected_language=lang,
            confidence=confidence,
            alternatives=alternatives,
        )
    except DetectionFailedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/languages",
    response_model=SupportedLanguagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List all supported language codes",
    description="Returns all BCP-47 codes supported by NLLB-200, sorted alphabetically.",
)
async def list_languages() -> SupportedLanguagesResponse:
    langs = sorted(
        [
            SupportedLanguage(code=bcp47, flores_code=flores)
            for bcp47, flores in BCP47_TO_FLORES.items()
        ],
        key=lambda x: x.code,
    )
    return SupportedLanguagesResponse(languages=langs, total=len(langs))


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Provider health check",
    description="Returns configuration status of all translation providers.",
)
async def health() -> HealthResponse:
    from providers.nllb import _model_state, NLLBProvider

    def _check(name: str) -> bool:
        try:
            if name == "google":
                from providers.google_translate import GoogleTranslateProvider
                return GoogleTranslateProvider().is_configured()
            elif name == "deepl":
                from providers.deepl import DeepLProvider
                return DeepLProvider().is_configured()
            elif name == "microsoft":
                from providers.microsoft import MicrosoftTranslatorProvider
                return MicrosoftTranslatorProvider().is_configured()
            elif name == "libretranslate":
                from providers.libretranslate import LibreTranslateProvider
                return LibreTranslateProvider().is_configured()
            elif name == "nllb":
                return NLLBProvider().is_configured()
        except Exception:
            return False
        return False

    providers = {
        name: _check(name)
        for name in ("google", "deepl", "microsoft", "libretranslate", "nllb")
    }
    nllb_loaded = _model_state.get("loaded", False)
    all_ok = any(providers.values())

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        providers=providers,
        nllb_loaded=nllb_loaded,
    )
