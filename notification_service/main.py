# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  main.py
# ───────────────────────────────────────────────────────────────────────────
"""
main.py
═══════════════════════════════════════════════════════════════════════════════
notification_service entry point.

Responsibilities on startup:
  · Database: create tables via SQLModel metadata (production uses Alembic)
  · Kafka consumer: subscribe to riviwa.notifications topic
  · APScheduler: start scheduled and retry jobs
  · Channel health check: log which providers are configured

Responsibilities on shutdown:
  · Stop Kafka consumer gracefully
  · Shutdown APScheduler
  · Close DB connection pool

Architecture notes (ignorance principle)
──────────────────────────────────────────────────────────────────────────────
  The notification_service does NOT know what "feedback acknowledged" means.
  It receives a notification request with:
    · notification_type  — template lookup key
    · variables          — template rendering data (provided by caller)
    · recipient          — who to contact (provided by caller)
    · channels           — how to contact them (or uses defaults)
    · scheduled_at       — when (null = now, future = reminder)

  All business logic (WHAT to notify about, WHO to notify, WHEN) lives in
  the originating service (auth_service, feedback_service, etc.).
  This service only handles HOW to deliver the notification.

Delivery flow (Uber/Bolt pattern)
──────────────────────────────────────────────────────────────────────────────
  [Source Service]
        │
        │  publishes to Kafka topic: riviwa.notifications
        │  (or calls POST /api/v1/internal/dispatch for synchronous OTPs)
        ▼
  [notification_service Kafka Consumer]
        │
        │  DeliveryService.process_request()
        ├─ idempotency check (skip duplicates)
        ├─ save Notification row to DB
        ├─ if scheduled_at future → save as PENDING_SCHEDULED, APScheduler will fire
        ├─ resolve channels (requested channels ∩ user preferences)
        ├─ load push tokens from NotificationDevice table
        │
        ▼
  [DeliveryService._dispatch()]
        │
        ├── for each channel:
        │     TemplateService.render(type, channel, language, variables)
        │     ChannelPayload assembled
        │     channel.send(payload)     ← provider call
        │     NotificationDelivery row created (status=SENT|FAILED|SKIPPED)
        │
        └── NotificationStatus updated (SENT|PARTIALLY_SENT|FAILED)

  [APScheduler]
        ├─ every 1 min:  dispatch_scheduled() — fire due reminders
        └─ every 5 min:  retry_failed_deliveries() — exponential backoff

  [Provider DLR Webhooks]  /api/v1/webhooks/*
        └─ update NotificationDelivery.status to DELIVERED when provider confirms
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.router import api_v1_router
from channels.email_channel import EmailChannel
from channels.push import PushChannel
from channels.sms import SMSChannel
from channels.whatsapp import WhatsAppChannel
from core.config import settings
from events.consumer import start_consumer, stop_consumer
from scheduler.jobs import create_scheduler

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("notification_service.starting",
             service=settings.SERVICE_NAME,
             environment=settings.ENVIRONMENT)

    # Database: create tables + seed default templates
    # In production, Alembic (entrypoint.sh) already ran; create_all is a no-op.
    # In development/staging, tables are created automatically.
    from db.init_db import init_db
    await init_db()

    # Log which channels are active
    channels_active = {
        "push":      PushChannel().is_configured(),
        "sms":       SMSChannel().is_configured(),
        "whatsapp":  WhatsAppChannel().is_configured(),
        "email":     EmailChannel().is_configured(),
        "in_app":    True,   # always available
    }
    log.info("notification_service.channels", **channels_active)

    # Start Kafka consumer
    await start_consumer()

    # Start APScheduler
    scheduler = create_scheduler()
    scheduler.start()
    log.info("notification_service.scheduler_started",
             job_count=len(scheduler.get_jobs()))

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("notification_service.stopping")
    await stop_consumer()
    scheduler.shutdown(wait=False)
    log.info("notification_service.stopped")


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Riviwa Notification Service",
        version="1.0.0",
        description=(
            "Centralised notification delivery service for the Riviwa platform. "
            "Handles push (FCM/APNs), SMS (Africa's Talking/Twilio), WhatsApp "
            "(Meta Cloud API), email (SendGrid/SMTP), and in-app notifications. "
            "\n\n"
            "**This service is ignorant of business logic.** "
            "Originating services (auth, feedback, stakeholder, payment) publish "
            "notification requests to Kafka or call POST /api/v1/internal/dispatch. "
            "This service handles delivery, retries, preferences, and scheduling."
        ),
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # In production/staging, CORS is handled by the nginx reverse proxy.
    # Only enable service-level CORS in development (direct access without nginx).
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.SERVICE_NAME}

    # ── Exception handlers ────────────────────────────────────────────────────
    from fastapi.responses import JSONResponse
    from core.exceptions import AppError

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code = exc.status_code,
            content     = exc.to_response_body(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request, exc: Exception):
        import structlog as _sl
        _sl.get_logger(__name__).error(
            "notification.unhandled_error", error=str(exc), path=str(request.url)
        )
        return JSONResponse(
            status_code = 500,
            content     = {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

    return app


app = create_app()
