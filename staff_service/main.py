"""main.py — staff_service FastAPI application."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

# Ensure all models are registered in SQLModel.metadata before DB init
import models  # noqa: F401

from core.config import settings
from core.exceptions import AppError
from db.session import engine
from sqlmodel import SQLModel

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("staff_service.startup.begin")

    # DB: create all tables (idempotent — alembic handles schema changes)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("staff_service.startup.db_ready")

    # Kafka producer
    from events.producer import get_producer
    producer = await get_producer()
    await producer.start()
    app.state.producer = producer
    log.info("staff_service.startup.kafka_producer_ready")

    # Kafka consumer
    from events.consumer import start_consumer
    await start_consumer()
    log.info("staff_service.startup.kafka_consumer_ready")

    # MinIO bucket
    from storage.minio_client import ensure_bucket_exists
    await ensure_bucket_exists()
    log.info("staff_service.startup.minio_ready")

    log.info("staff_service.startup.complete", port=8135)
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("staff_service.shutdown.begin")
    from events.consumer import stop_consumer
    await stop_consumer()
    await app.state.producer.stop()
    await engine.dispose()
    log.info("staff_service.shutdown.complete")


app = FastAPI(
    title="Riviwa Staff Service",
    description=(
        "Staff identity verification for the Riviwa platform. "
        "Organisations register staff with unique codes and QR badges; "
        "citizens verify identity by scanning or typing the staff code."
    ),
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan,
)

# CORS — only in development (prod handled by Nginx)
if settings.ENVIRONMENT != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())


@app.exception_handler(PydanticValidationError)
async def validation_error_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("staff_service.unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

from api.v1.router import api_router  # noqa: E402

app.include_router(api_router)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}
