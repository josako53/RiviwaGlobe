"""
main.py — FastAPI application factory for ai_service.
Lifespan: DB init → Qdrant collection setup → Kafka producer → Kafka consumer
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncIterator
import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from db.init_db import init_db
from events.producer import get_producer, close_producer
from events.consumer import start_consumer, stop_consumer
from services.ollama_service import get_ollama, close_ollama

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("ai.startup.db")
    await init_db()
    log.info("ai.startup.db_ready")

    # Warm up the embedding model (loads sentence-transformers into memory)
    try:
        from services.rag_service import _get_model, _get_qdrant
        _get_model()
        _get_qdrant()
        log.info("ai.startup.rag_ready")
    except Exception as exc:
        log.warning("ai.startup.rag_failed", error=str(exc))

    # Check Ollama connectivity
    try:
        ollama_ok = await get_ollama().health_check()
        if ollama_ok:
            log.info("ai.startup.ollama_ready", model=settings.OLLAMA_MODEL)
        else:
            log.warning("ai.startup.ollama_not_ready", model=settings.OLLAMA_MODEL,
                        hint="Ollama may still be pulling the model — conversations will retry automatically.")
    except Exception as exc:
        log.warning("ai.startup.ollama_check_failed", error=str(exc))

    try:
        await get_producer()
        log.info("ai.startup.kafka_producer_ready")
    except Exception as exc:
        log.error("ai.startup.kafka_producer_failed", error=str(exc))

    try:
        await start_consumer()
        log.info("ai.startup.kafka_consumer_ready")
    except Exception as exc:
        log.error("ai.startup.kafka_consumer_failed", error=str(exc))

    log.info("ai.startup.complete", service=settings.AI_SERVICE_NAME)
    yield

    await stop_consumer()
    await close_producer()
    await close_ollama()
    log.info("ai.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa AI Service",
        version="1.0.0",
        description=(
            "Rivai AI — conversational feedback collection for GRM. "
            "Handles PAP conversations via SMS, WhatsApp, phone call, web, and mobile. "
            "Uses Ollama LLM + Qdrant RAG to auto-identify projects, collect feedback fields, "
            "and submit to feedback_service."
        ),
        docs_url    = "/docs"         if settings.ENVIRONMENT != "production" else None,
        redoc_url   = "/redoc"        if settings.ENVIRONMENT != "production" else None,
        openapi_url = "/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning("ai.app_error", error_code=exc.error_code, path=str(request.url.path))
        return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": "VALIDATION_ERROR", "message": "Invalid request.", "details": details},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("ai.unhandled", path=str(request.url.path), error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        ollama_ok = await get_ollama().health_check()
        return {
            "status": "ok",
            "service": settings.AI_SERVICE_NAME,
            "ollama": "ready" if ollama_ok else "unavailable",
            "model": settings.OLLAMA_MODEL,
        }

    return app


app = create_app()
