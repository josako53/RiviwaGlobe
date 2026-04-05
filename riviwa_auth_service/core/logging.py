"""
core/logging.py
═══════════════════════════════════════════════════════════════════════════════
Structured logging for the Riviwa auth service.

Stack
─────
  structlog ≥ 23   — structured, context-aware logging
  stdlib logging   — underlying handler / ProcessorFormatter bridge

Output
──────
  LOG_FORMAT=json     → NDJSON on stdout  (production / Docker / Loki)
  LOG_FORMAT=console  → coloured human text  (local dev, default)

Every log record always includes
──────────────────────────────────
  timestamp    ISO-8601 UTC
  level        debug | info | warning | error | critical
  logger       module __name__
  event        the message string
  service      riviwa_auth_service  (from settings)
  environment  production | staging | development | test

Per-request context  (injected by LoggingMiddleware before the route handler)
─────────────────────────────────────────────────────────────────────────────
  request_id   uuid4 per HTTP request
  http_method  GET | POST | …
  http_path    /api/v1/auth/login
  client_ip    real IP (X-Forwarded-For stripped when TRUST_PROXY=True)

Per-identity context  (injected by get_current_user dependency)
────────────────────────────────────────────────────────────────
  user_id      authenticated user UUID
  org_id       active org UUID  (present only when in an org dashboard)

Usage anywhere in the codebase
───────────────────────────────
    import structlog
    log = structlog.get_logger(__name__)

    log.info("user.registered",   user_id=str(user.id))
    log.warning("fraud.blocked",  score=92, ip=ip_address)
    log.error("kafka.failed",     topic="riviwa.user.events", exc_info=exc)

Bootstrap (call once before the first log statement)
─────────────────────────────────────────────────────
    # main.py  lifespan / startup
    from app.core.logging import configure_logging
    configure_logging()
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import logging.config
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Custom processors
# ─────────────────────────────────────────────────────────────────────────────

def _add_service_context(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Stamp every log record with static service-level metadata."""
    event_dict.setdefault("service",     settings.RIVIWA_AUTH_SERVICE_NAME)
    event_dict.setdefault("environment", getattr(settings, "ENVIRONMENT", "production"))
    return event_dict


def _drop_color_message(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Remove uvicorn's color_message key that pollutes JSON output."""
    event_dict.pop("color_message", None)
    return event_dict


def _reorder_keys(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """
    Promote high-signal fields to the front so log streams are scannable.

    Order: timestamp · level · logger · event · service · environment ·
           request_id · user_id · org_id · (remaining keys)
    """
    priority = [
        "timestamp", "level", "logger", "event",
        "service", "environment",
        "request_id", "user_id", "org_id",
    ]
    ordered: dict[str, Any] = {}
    for key in priority:
        if key in event_dict:
            ordered[key] = event_dict.pop(key)
    ordered.update(event_dict)
    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# Shared processor chain  (applied regardless of output format)
# ─────────────────────────────────────────────────────────────────────────────

SHARED_PROCESSORS: list[Processor] = [
    # Merge per-request fields bound via structlog.contextvars
    structlog.contextvars.merge_contextvars,
    # Inject logger name (__name__) and level string
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    # ISO-8601 timestamp in UTC
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    # Render stack_info= kwarg as a string when present
    structlog.processors.StackInfoRenderer(),
    # Render exc_info= into a structured dict (not a raw traceback string)
    structlog.processors.dict_tracebacks,
    _drop_color_message,
    _add_service_context,
    _reorder_keys,
]


# ─────────────────────────────────────────────────────────────────────────────
# configure_logging()
# ─────────────────────────────────────────────────────────────────────────────

def configure_logging() -> None:
    """
    Wire structlog + stdlib logging together.

    Reads from settings (all optional with sensible defaults):
        LOG_LEVEL   DEBUG | INFO | WARNING | ERROR   (default INFO)
        LOG_FORMAT  json | console                   (default console)
        SQL_ECHO    bool                             (default False)

    Call exactly once at application startup before any log statement fires.
    """
    log_level_name: str = getattr(settings, "LOG_LEVEL",  "INFO").upper()
    log_format:     str = getattr(settings, "LOG_FORMAT", "console").lower()

    # Choose the terminal renderer
    if log_format == "json":
        final_renderer: Processor = structlog.processors.JSONRenderer()
    else:
        final_renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )

    # ── stdlib root logger config ─────────────────────────────────────────────
    # structlog wraps stdlib via ProcessorFormatter so third-party libraries
    # (SQLAlchemy, uvicorn, aiokafka) also emit structured records.
    logging.config.dictConfig({
        "version":                  1,
        "disable_existing_loggers": False,

        "formatters": {
            "structured": {
                "()":        structlog.stdlib.ProcessorFormatter,
                "processor": final_renderer,
                # Applied to stdlib LogRecords from third-party libraries
                "foreign_pre_chain": SHARED_PROCESSORS,
            },
        },

        "handlers": {
            "stdout": {
                "class":     "logging.StreamHandler",
                "formatter": "structured",
                "stream":    "ext://sys.stdout",
            },
        },

        "root": {
            "handlers": ["stdout"],
            "level":    log_level_name,
        },

        # Third-party logger verbosity
        "loggers": {
            "uvicorn":           {"level": "INFO",    "propagate": True},
            "uvicorn.error":     {"level": "INFO",    "propagate": True},
            "uvicorn.access":    {"level": "WARNING", "propagate": True},
            "aiokafka":          {"level": "WARNING", "propagate": True},
            "passlib":           {"level": "ERROR",   "propagate": True},
            "sqlalchemy.engine": {
                "level":     "INFO" if getattr(settings, "SQL_ECHO", False) else "WARNING",
                "propagate": True,
            },
        },
    })

    # ── structlog configuration ───────────────────────────────────────────────
    structlog.configure(
        processors=[
            *SHARED_PROCESSORS,
            # Bridge structlog bound loggers into the stdlib handler above
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level_name, logging.INFO)
        ),
        cache_logger_on_first_use=True,
        context_class=dict,
    )

    structlog.get_logger("app.core.logging").info(
        "logging.configured",
        level=log_level_name,
        format=log_format,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-request context helpers  (called from LoggingMiddleware)
# ─────────────────────────────────────────────────────────────────────────────

def bind_request_context(
    *,
    request_id: str,
    method:     str,
    path:       str,
    client_ip:  str,
) -> None:
    """
    Bind per-request fields into structlog's contextvars store.

    Call in LoggingMiddleware BEFORE awaiting the next handler.
    Pair with clear_request_context() in a finally block so context never
    leaks across requests in the same asyncio task.

    Every log call that executes within the same asyncio task will
    automatically carry these fields — no manual passing required.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        http_method=method,
        http_path=path,
        client_ip=client_ip,
    )


def bind_user_to_context(
    user_id: str,
    org_id:  str | None = None,
) -> None:
    """
    Enrich the running request context with identity fields.

    Call from the get_current_user dependency after JWT verification succeeds
    so that all subsequent log calls in this request carry user identity.
    """
    structlog.contextvars.bind_contextvars(
        user_id=user_id,
        **({"org_id": org_id} if org_id else {}),
    )


def clear_request_context() -> None:
    """
    Wipe all per-request context from the contextvars store.
    Call in the LoggingMiddleware finally block — never skip this.
    """
    structlog.contextvars.clear_contextvars()
