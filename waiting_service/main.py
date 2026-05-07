from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from db.init_db import init_db
from db.session import AsyncSessionLocal
from events.consumer import start_consumer, stop_consumer
from events.producer import close_producer, get_producer
from waiting_redis.client import close_redis, get_redis_client, init_redis
from scheduler.jobs import create_scheduler

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("waiting.startup.db")
    await init_db()

    log.info("waiting.startup.redis")
    redis = await init_redis(settings.REDIS_URL)

    producer = None
    try:
        producer = await get_producer()
        log.info("waiting.startup.kafka_producer_ready")
    except Exception as exc:
        log.error("waiting.startup.kafka_producer_failed", error=str(exc))

    try:
        await start_consumer()
        log.info("waiting.startup.kafka_consumer_ready")
    except Exception as exc:
        log.error("waiting.startup.kafka_consumer_failed", error=str(exc))

    scheduler = None
    if producer and redis:
        try:
            scheduler = create_scheduler(
                db_factory=AsyncSessionLocal,
                redis=redis,
                producer=producer,
            )
            scheduler.start()
            log.info("waiting.startup.scheduler_ready")
        except Exception as exc:
            log.error("waiting.startup.scheduler_failed", error=str(exc))

    log.info("waiting.startup.complete", service=settings.SERVICE_NAME)
    yield

    if scheduler:
        scheduler.shutdown(wait=False)
    await stop_consumer()
    await close_producer()
    await close_redis()
    log.info("waiting.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title       = "Riviwa Waiting Service",
        version     = "1.0.0",
        description = "Real-time queue management — tickets, priority, ETA, staff counters, analytics",
        docs_url    = "/docs"         if settings.ENVIRONMENT != "production" else None,
        redoc_url   = "/redoc"        if settings.ENVIRONMENT != "production" else None,
        openapi_url = "/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan    = lifespan,
    )

    if settings.ENVIRONMENT in ("development", "staging"):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning("waiting.app_error", error_code=exc.error_code, path=str(request.url.path))
        return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "VALIDATION_ERROR", "message": "Invalid request.", "details": details})

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("waiting.unhandled", path=str(request.url.path), error=str(exc), exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."})

    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok", "service": settings.SERVICE_NAME}

    return app


app = create_app()
