"""
main.py — FastAPI application factory for feedback_service.
Lifespan: DB tables → Kafka producer → Kafka consumer
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
    log.info("feedback.startup.db")
    await init_db()
    log.info("feedback.startup.db_ready")
    try:
        await get_producer()
        log.info("feedback.startup.kafka_producer_ready")
    except Exception as exc:
        log.error("feedback.startup.kafka_producer_failed", error=str(exc))
    try:
        await start_consumer()
        log.info("feedback.startup.kafka_consumer_ready")
    except Exception as exc:
        log.error("feedback.startup.kafka_consumer_failed", error=str(exc))
    log.info("feedback.startup.complete", service=settings.FEEDBACK_SERVICE_NAME)
    yield
    await stop_consumer()
    await close_producer()
    log.info("feedback.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Feedback Service",
        version="1.0.0",
        description="Grievances · Suggestions · Applause · GRM escalation · Committee management · Reports",
        docs_url    ="/docs"         if settings.ENVIRONMENT != "production" else None,
        redoc_url   ="/redoc"        if settings.ENVIRONMENT != "production" else None,
        openapi_url ="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )
    # CORS handled by nginx in production; only enable in dev for direct access
    if settings.ENVIRONMENT == "development":
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning("feedback.app_error", error_code=exc.error_code, path=str(request.url.path))
        return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "VALIDATION_ERROR", "message": "Invalid request.", "details": details})

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("feedback.unhandled", path=str(request.url.path), error=str(exc), exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."})

    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok", "service": settings.FEEDBACK_SERVICE_NAME}

    return app


app = create_app()
