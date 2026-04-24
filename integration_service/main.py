"""
main.py — integration_service FastAPI application.

Provides third-party integration capabilities:
  - Partner client registration + API key management
  - OAuth2 Authorization Code + PKCE / Client Credentials flows
  - Context sessions (partner pushes pre-fill data for widget/mini-app)
  - JS widget / mini-app embed sessions
  - Webhook engine with signed delivery + exponential backoff retry
  - External data bridge (Riviwa pulls from partner endpoint)
  - Audit logging middleware (every request logged to integration_audit_logs)
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
import structlog.stdlib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from core.config import settings
from db.session import engine

log = structlog.get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB tables (Alembic handles schema; this is a safety net for clean envs)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("integration_service.db_ready")

    # Start webhook delivery scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _webhook_poll,
        trigger="interval",
        seconds=15,
        id="webhook_delivery",
        replace_existing=True,
    )
    scheduler.start()
    log.info("integration_service.scheduler_started")

    yield

    scheduler.shutdown(wait=False)
    await engine.dispose()


async def _webhook_poll():
    from services.webhook_worker import process_pending_deliveries
    try:
        await process_pending_deliveries()
    except Exception as exc:
        log.error("webhook_worker.error", error=str(exc))


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Riviwa Integration Service",
    description=(
        "Third-party integration API — mini-app embedding, website widget/tag, "
        "AI chatbot integration, OAuth2 PKCE, API key management, "
        "webhook engine, and external data bridge."
    ),
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Per-request origin check is in widget.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next) -> Response:
    """Log every API call to integration_audit_logs."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)

    # Extract client_id from request state if auth succeeded
    client_id = getattr(request.state, "client_id", None)

    # Fire-and-forget audit log
    try:
        from db.session import AsyncSessionLocal
        from models.integration import IntegrationAuditLog

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else None
        )

        async with AsyncSessionLocal() as db:
            entry = IntegrationAuditLog(
                client_id   = uuid.UUID(client_id) if client_id else None,
                method      = request.method,
                path        = str(request.url.path),
                status_code = response.status_code,
                duration_ms = duration_ms,
                ip_address  = ip,
                user_agent  = request.headers.get("user-agent", "")[:512],
            )
            db.add(entry)
            await db.commit()
    except Exception:
        pass   # Never block the response for audit logging

    return response


# ── Routers ───────────────────────────────────────────────────────────────────

from api.v1 import clients, oauth, context, widget, webhooks   # noqa: E402

app.include_router(clients.router,  prefix="/api/v1")
app.include_router(oauth.router,    prefix="/api/v1")
app.include_router(context.router,  prefix="/api/v1")
app.include_router(widget.router,   prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "service": "integration_service"}
