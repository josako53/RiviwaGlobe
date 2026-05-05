"""main.py — qr_service FastAPI application."""
from __future__ import annotations
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from models.qr import QRCode, QRScan, ReceiptSession, QRBatch  # noqa: ensure metadata

from core.config import settings
from db.session import engine

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("qr_service.db_ready")

    # Start Kafka consumer (non-fatal if Kafka unavailable)
    from events.consumer import start_consumer
    await start_consumer()

    yield

    from events.consumer import stop_consumer
    await stop_consumer()
    await engine.dispose()


app = FastAPI(
    title="Riviwa QR Service",
    description=(
        "QR code and SMS short code generation, management, and verification. "
        "Supports receipt QR codes, sticky location QR codes, bulk product QR batches, "
        "and unified org-prefixed SMS codes (UTT-XXXXXX, CRDB-XXXXXX …)."
    ),
    version="2.0.0",
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

from api.v1.qr      import router as qr_router
from api.v1.internal import router as internal_router
from api.v1.public   import router as public_router

app.include_router(qr_router)
app.include_router(internal_router)
app.include_router(public_router)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "service": "qr_service"}
