"""main.py — subscription_service FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

from core.config import settings
from core.exceptions import AppError
from db.session import engine
from db.seed import seed_plans_and_addons
from db.session import AsyncSessionLocal
from events.producer import get_producer, stop_producer
from events.consumer import start_consumer, stop_consumer

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("subscription_service.db_ready")

    # Seed plans and add-ons
    async with AsyncSessionLocal() as session:
        await seed_plans_and_addons(session)

    # Kafka producer + consumer
    await get_producer()
    await start_consumer()
    log.info("subscription_service.startup.complete")

    yield

    await stop_consumer()
    await stop_producer()
    await engine.dispose()
    log.info("subscription_service.shutdown")


app = FastAPI(
    title="Riviwa Subscription Service",
    description=(
        "Manages Riviwa SaaS subscriptions: plans, checkout, billing, "
        "invoices, promo codes, usage metering, and payment gateway integration."
    ),
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("subscription_service.unhandled_error", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR",
                                                   "message": "An unexpected error occurred."})


from api.v1.router import api_v1_router
app.include_router(api_v1_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "subscription_service"}
