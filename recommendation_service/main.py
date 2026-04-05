"""
main.py — Recommendation service entry point.

Lifespan:
  1. Database: create tables + PostGIS extension
  2. Redis: connect cache
  3. Qdrant: ensure collection exists
  4. Embedding model: load sentence-transformer
  5. Kafka consumer: subscribe to entity/activity events

Shutdown:
  1. Stop Kafka consumer
  2. Close Redis
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from db.init_db import init_db
from events.consumer import start_consumer, stop_consumer
from services import cache_service, embedding_service

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 1. Database ───────────────────────────────────────────────────────────
    log.info("rec.startup.db")
    await init_db()
    log.info("rec.startup.db_ready")

    # ── 2. Redis ──────────────────────────────────────────────────────────────
    log.info("rec.startup.redis")
    try:
        await cache_service.init_redis()
        log.info("rec.startup.redis_ready")
    except Exception as exc:
        log.warning("rec.startup.redis_failed", error=str(exc))

    # ── 3. Qdrant ─────────────────────────────────────────────────────────────
    log.info("rec.startup.qdrant")
    try:
        await embedding_service.ensure_collection()
        log.info("rec.startup.qdrant_ready")
    except Exception as exc:
        log.warning("rec.startup.qdrant_failed", error=str(exc))

    # ── 4. Embedding model ────────────────────────────────────────────────────
    log.info("rec.startup.embedding")
    try:
        await embedding_service.load_model()
        log.info("rec.startup.embedding_ready")
    except Exception as exc:
        log.warning("rec.startup.embedding_failed", error=str(exc))

    # ── 5. Kafka consumer ─────────────────────────────────────────────────────
    log.info("rec.startup.kafka")
    try:
        await start_consumer()
        log.info("rec.startup.kafka_ready")
    except Exception as exc:
        log.warning("rec.startup.kafka_failed", error=str(exc))

    log.info("rec.startup.complete", service=settings.SERVICE_NAME)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await stop_consumer()
    await cache_service.close_redis()
    log.info("rec.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Recommendation Service",
        description="Relevance-based recommendations using semantic similarity, tag overlap, geo proximity, and activity signals.",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS — only in development (nginx handles CORS in prod/staging)
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_v1_router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        from schemas.recommendation import HealthResponse
        return HealthResponse(
            status="ok",
            database=True,
            qdrant=embedding_service.is_qdrant_available(),
            redis=cache_service.is_redis_available(),
            embedding_model_loaded=embedding_service.is_model_loaded(),
        )

    # ── Error handler ─────────────────────────────────────────────────────────
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    return app


app = create_app()
