"""
app/main.py
═══════════════════════════════════════════════════════════════════════════════
FastAPI application factory for the Riviwa Auth Service.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Run via Docker:
    docker compose up --build

Lifespan order (startup)
─────────────────────────
  1. PostgreSQL: create tables + seed initial admin  (with 5× retry / backoff)
  2. Redis: ping to verify connectivity
  3. Kafka: initialise producer singleton

Lifespan order (shutdown)
──────────────────────────
  1. Kafka: flush pending messages + close producer
  2. Redis / PostgreSQL: closed automatically

Exception handlers
──────────────────
  AppError subclasses      → ErrorResponse JSON  (status from AppError.status_code)
  RequestValidationError   → HTTP 422  (per-field ErrorDetail list)
  Unhandled Exception      → HTTP 500  (detail suppressed in production)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
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
from db.session import init_redis, get_redis_client, close_redis
from events.consumer import start_consumer, stop_consumer
from workers.kafka_producer import get_kafka_producer, close_kafka_producer

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan — startup & shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manages the full startup/shutdown lifecycle.

    startup order: Postgres → Redis → Kafka
    shutdown order: Kafka → (Redis + Postgres auto-closed)
    """
    # ── 1. Database: create tables + seed ────────────────────────────────────
    # Retries internally up to 5× with exponential back-off.
    # Raises RuntimeError (and aborts startup) if Postgres is unreachable.
    log.info("riviwa_auth.startup.db")
    await init_db()
    log.info("riviwa_auth.startup.db_ready")

    # ── 2. Redis: verify connectivity ────────────────────────────────────────
    log.info("riviwa_auth.startup.redis")
    try:
        await init_redis()
        redis = await get_redis_client()
        await redis.ping()
        log.info("riviwa_auth.startup.redis_ready")
    except Exception as exc:
        log.error("riviwa_auth.startup.redis_failed", error=str(exc))
        raise RuntimeError(
            "Application startup aborted: Redis unreachable."
        ) from exc

    # ── 3. Kafka: initialise producer ─────────────────────────────────────────
    log.info("riviwa_auth.startup.kafka")
    try:
        await get_kafka_producer()
        log.info("riviwa_auth.startup.kafka_ready")
    except Exception as exc:
        # Kafka failure is logged but does NOT abort startup.
        # Events will fail gracefully; producer retries on next publish.
        log.error(
            "riviwa_auth.startup.kafka_failed",
            error=str(exc),
            note="Service starting without Kafka — events will fail until reconnected.",
        )

    log.info(
        "riviwa_auth.startup.complete",
        service=settings.RIVIWA_AUTH_SERVICE_NAME,
    )

    # ── 4. Kafka consumer: sync User.language from translation_service ────────
    try:
        await start_consumer()
        log.info("riviwa_auth.startup.consumer_ready")
    except Exception as exc:
        log.error("riviwa_auth.startup.consumer_failed", error=str(exc))

    # ── Hand control to FastAPI ───────────────────────────────────────────────
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await stop_consumer()
    log.info("riviwa_auth.shutdown.redis")
    await close_redis()
    log.info("riviwa_auth.shutdown.kafka")
    await close_kafka_producer()
    log.info("riviwa_auth.shutdown.complete")


# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:
    """
    Must be called OUTSIDE the lifespan context — exception handlers are
    part of the app architecture, not runtime events.
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning(
            "app_error",
            error_code=exc.error_code,
            status_code=exc.status_code,
            message=exc.message,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response_body(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc:     RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "field":   ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error":   "VALIDATION_ERROR",
                "message": "Request body is invalid.",
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        request: Request,
        exc:     Exception,
    ) -> JSONResponse:
        log.error(
            "unhandled_exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error":   "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Auth Service",
        version="1.0.0",
        description=(
            "Authentication · Registration · User management · "
            "Organisation lifecycle · Fraud detection"
        ),
        docs_url    ="/docs"          if getattr(settings, "ENVIRONMENT", "development") != "production" else None,
        redoc_url   ="/redoc"         if getattr(settings, "ENVIRONMENT", "development") != "production" else None,
        openapi_url ="/openapi.json"  if getattr(settings, "ENVIRONMENT", "development") != "production" else None,
        lifespan=application_lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production, CORS is handled by the nginx reverse proxy.
    # Only enable service-level CORS in development (direct access without nginx).
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins    =getattr(settings, "ALLOWED_ORIGINS", ["*"]),
            allow_credentials=True,
            allow_methods    =["*"],
            allow_headers    =["*"],
        )

    # ── Exception handlers ────────────────────────────────────────────────────
    _register_exception_handlers(app)

    # ── API routers ───────────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    # ── Health probe (no auth — for Docker / load-balancer) ──────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_check() -> dict:
        return {"status": "ok", "service": settings.RIVIWA_AUTH_SERVICE_NAME}

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Module-level instance — used by uvicorn and docker-compose
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()
