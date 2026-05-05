"""main.py — verification_service FastAPI application."""
from __future__ import annotations
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from core.config import settings
from db.session import engine

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("verification_service.db_ready")
    yield
    await engine.dispose()


app = FastAPI(
    title="Riviwa Verification Service",
    description=(
        "Product and service authenticity verification via QR codes and short codes. "
        "Handles genuine/used/unrecognized results, fake product reporting with GPS and photo, "
        "field agent management, and counterfeit heatmap analytics."
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

from api.v1.verify  import router as verify_router
from api.v1.reports import router as reports_router
from api.v1.stats   import router as stats_router

app.include_router(verify_router)
app.include_router(reports_router)
app.include_router(stats_router)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "service": "verification_service"}
