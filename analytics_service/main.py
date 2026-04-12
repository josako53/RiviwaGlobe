"""
main.py — FastAPI application factory for analytics_service.
Lifespan: analytics_db table creation via SQLModel.metadata.create_all.
No Kafka — this service only reads from feedback_db and writes to analytics_db.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from db.session import analytics_engine

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("analytics.startup.db_init")
    try:
        # Import all models so SQLModel.metadata sees all tables
        from models.analytics import (  # noqa: F401
            CommitteePerformance,
            FeedbackMLScore,
            FeedbackSLAStatus,
            GeneratedReport,
            HotspotAlert,
            StaffLogin,
        )
        async with analytics_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        log.info("analytics.startup.db_tables_ready")
    except Exception as exc:
        log.error("analytics.startup.db_init_failed", error=str(exc), exc_info=exc)
        raise

    log.info(
        "analytics.startup.complete",
        service=settings.ANALYTICS_SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        port=8095,
    )

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await analytics_engine.dispose()
    log.info("analytics.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Analytics Service",
        version="1.0.0",
        description=(
            "Pre-computed and real-time analytics for the Riviwa GRM platform. "
            "Provides feedback metrics, SLA compliance, hotspot detection, "
            "committee performance, staff activity, and AI-powered insights."
        ),
        docs_url    ="/docs"         if settings.ENVIRONMENT != "production" else None,
        redoc_url   ="/redoc"        if settings.ENVIRONMENT != "production" else None,
        openapi_url ="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS handled by nginx in production; only enable in dev
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning(
            "analytics.app_error",
            error_code=exc.error_code,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response_body(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error":   "VALIDATION_ERROR",
                "message": "Invalid request.",
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "analytics.unhandled",
            path=str(request.url.path),
            error=str(exc),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error":   "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
        )

    app.include_router(api_v1_router)

    @app.get("/health/analytics", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        return {
            "status":      "ok",
            "service":     settings.ANALYTICS_SERVICE_NAME,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_root() -> dict:
        return {"status": "ok", "service": settings.ANALYTICS_SERVICE_NAME}

    return app


app = create_app()
