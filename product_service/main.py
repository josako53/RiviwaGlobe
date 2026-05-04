from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from core.config import settings
from core.exceptions import AppError
from api.v1.router import api_router
from events.producer import get_producer
from events.consumer import start_consumer, stop_consumer

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    log.info("product_service.startup.begin")

    # Kafka producer
    log.info("product_service.startup.kafka_producer")
    producer = await get_producer()
    await producer.start()
    app.state.producer = producer
    log.info("product_service.startup.kafka_producer_ready")

    # Kafka consumer (org events → org_cache)
    log.info("product_service.startup.kafka_consumer")
    await start_consumer()
    log.info("product_service.startup.kafka_consumer_ready")

    log.info("product_service.startup.complete", service=settings.SERVICE_NAME, port=8110)
    yield

    # ── Shutdown ──────────────────────────────────────────────────
    log.info("product_service.shutdown.begin")
    await stop_consumer()
    await app.state.producer.stop()
    log.info("product_service.shutdown.complete")


app = FastAPI(
    title="Riviwa Product Service",
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
        content={"error_code": "VALIDATION_ERROR", "message": "Request validation failed", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("product_service.unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}
