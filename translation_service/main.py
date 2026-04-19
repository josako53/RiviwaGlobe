# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  main.py
# ───────────────────────────────────────────────────────────────────────────
"""
main.py — translation_service FastAPI application entry point.

Lifespan
────────
  startup:
    1. Load NLLB-200 model into memory (if NLLB_ENABLED=true and model dir
       exists — download_model.py must have been run first via entrypoint.sh).
  shutdown:
    1. No-op (model unloads with process).

Providers
─────────
  Primary (cloud):   Set TRANSLATION_PROVIDER=google|deepl|microsoft
  Local fallback:    NLLB-200 — always last in the provider chain.
  No-config mode:    TRANSLATION_PROVIDER=nllb — pure local, zero cloud calls.

Port: 8050
"""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from events.producer import get_producer, close_producer
from events.consumer import start_consumer, stop_consumer

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info(
        "translation_service.starting",
        service=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        nllb_enabled=settings.NLLB_ENABLED,
    )

    # ── Load NLLB model ───────────────────────────────────────────────────────
    if settings.NLLB_ENABLED:
        try:
            from providers.nllb import NLLBProvider
            provider = NLLBProvider()
            if provider.is_configured():
                provider.load()
                log.info("translation_service.nllb_loaded", model=settings.NLLB_MODEL_NAME)
            else:
                log.warning(
                    "translation_service.nllb_not_loaded",
                    reason="model directory missing or .download_complete marker not found",
                    model_dir=settings.NLLB_MODEL_DIR,
                    hint="Run: python download_model.py  (or entrypoint.sh handles this)",
                )
        except Exception as exc:
            log.error("translation_service.nllb_load_failed", error=str(exc))
            # Don't crash — cloud providers can still serve requests
    else:
        log.info("translation_service.nllb_disabled")

    # ── Start Kafka producer ──────────────────────────────────────────────────
    try:
        await get_producer()
        log.info("translation_service.kafka_producer_ready")
    except Exception as exc:
        log.error("translation_service.kafka_producer_failed", error=str(exc))
        # Non-fatal — translation still works, events just won't publish

    # ── Start Kafka consumer (user.registered → auto-create preferences) ──────
    try:
        await start_consumer()
        log.info("translation_service.kafka_consumer_ready")
    except Exception as exc:
        log.error("translation_service.kafka_consumer_failed", error=str(exc))

    log.info("translation_service.ready")
    yield

    log.info("translation_service.shutdown")
    await stop_consumer()
    await close_producer()


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Riviwa Translation Service",
    description=(
        "Multilingual translation and language detection for the Riviwa platform.\n\n"
        "**Primary use cases:**\n"
        "- Translating Consumer feedback (Swahili → English) for GRM staff\n"
        "- Translating notification templates into user-preferred languages\n"
        "- Translating SMS/WhatsApp channel session messages in real time\n"
        "- Language detection for incoming voice/text feedback\n\n"
        "**Provider chain:** Google Cloud → Microsoft → DeepL → LibreTranslate → **NLLB-200 (local)**\n\n"
        "NLLB-200 supports 200 languages including Swahili, Amharic, Hausa, Yoruba, "
        "Zulu, and 190+ others — zero external API calls required."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_body(),
    )

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "translation_service", "status": "ok", "docs": "/docs"}


@app.get("/ping", include_in_schema=False)
async def ping() -> dict:
    return {"pong": True}
