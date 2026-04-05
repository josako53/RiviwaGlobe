"""
main.py
═══════════════════════════════════════════════════════════════════════════════
FastAPI application factory for stakeholder_service.

Lifespan (startup)
──────────────────
  1. PostgreSQL: create tables via SQLModel.metadata.create_all
  2. Kafka producer: initialise singleton
  3. Kafka consumer: start background task (listens to org + feedback events)

Lifespan (shutdown)
──────────────────
  1. Kafka consumer: cancel task
  2. Kafka producer: flush + close
═══════════════════════════════════════════════════════════════════════════════
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

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 1. Database
    log.info("stakeholder.startup.db")
    await init_db()
    log.info("stakeholder.startup.db_ready")

    # 2. Kafka producer
    log.info("stakeholder.startup.kafka_producer")
    try:
        await get_producer()
        log.info("stakeholder.startup.kafka_producer_ready")
    except Exception as exc:
        log.error("stakeholder.startup.kafka_producer_failed", error=str(exc))

    # 3. Kafka consumer (background task — listens to org + feedback events)
    log.info("stakeholder.startup.kafka_consumer")
    try:
        await start_consumer()
        log.info("stakeholder.startup.kafka_consumer_ready")
    except Exception as exc:
        log.error("stakeholder.startup.kafka_consumer_failed", error=str(exc))

    log.info("stakeholder.startup.complete", service=settings.STAKEHOLDER_SERVICE_NAME)

    yield

    # Shutdown
    await stop_consumer()
    await close_producer()
    log.info("stakeholder.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Stakeholder Service",
        version="1.0.0",
        description=(
            "Stakeholder registration · Engagement activities · "
            "Communication tracking · Focal persons · Project cache sync"
        ),
        docs_url    ="/docs"         if settings.ENVIRONMENT != "production" else None,
        redoc_url   ="/redoc"        if settings.ENVIRONMENT != "production" else None,
        openapi_url ="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS handled by nginx in production; only enable in dev for direct access
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ── Exception handlers ─────────────────────────────────────────────────────

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning("stakeholder.app_error", error_code=exc.error_code,
                    status_code=exc.status_code, path=str(request.url.path))
        return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "VALIDATION_ERROR", "message": "Request body is invalid.", "details": details},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("stakeholder.unhandled_exception", path=str(request.url.path), error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok", "service": settings.STAKEHOLDER_SERVICE_NAME}

    return app


app = create_app()
