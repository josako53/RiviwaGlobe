"""
payment_service — main.py
FastAPI application with async lifespan, exception handlers, and health endpoint.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import AppError
from db.init_db import init_db
from events.producer import stop_producer

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("payment_service.starting", env=settings.ENVIRONMENT)
    await init_db()
    log.info("payment_service.ready", port=settings.PORT)
    yield
    await stop_producer()
    log.info("payment_service.shutdown")


app = FastAPI(
    title="Riviwa Payment Service",
    version="1.0.0",
    description=(
        "Handles payment intents, provider initiation (AzamPay · Selcom · M-Pesa), "
        "webhook reconciliation, and refunds for the Riviwa platform."
    ),
    lifespan=lifespan,
)

app.include_router(api_v1_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.get("/health", tags=["Health"], include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "payment_service"}


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "Riviwa Payment Service", "version": "1.0.0"}
