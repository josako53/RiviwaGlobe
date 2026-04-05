"""
workers/celery_app.py
──────────────────────────────────────────────────────────────────
Celery application configuration + beat schedule.

Background tasks
──────────────────────────────────────────────────────────────────
  score_behavioral_ml             immediate, on every registration
  analyze_duplicate_graph         immediate, on every registration
  cleanup_expired_verifications   daily beat  — 03:00 UTC
  recheck_warn_accounts           hourly beat — :00

Queue topology
──────────────────────────────────────────────────────────────────
  fraud_high    — latency-sensitive fraud tasks (high-priority)
  maintenance   — periodic housekeeping (low-priority, separate workers)

Workers should be started with --queues flags to keep the queues
isolated and independently scalable:
  celery -A workers.celery_app worker -Q fraud_high -c 4
  celery -A workers.celery_app worker -Q maintenance -c 1
  celery -A workers.celery_app beat   --scheduler celery.beat.PersistentScheduler
"""
from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "auth_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.fraud_tasks"],
)

celery_app.conf.update(
    # ── Serialisation ─────────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # ── Reliability ───────────────────────────────────────────────────────────
    task_acks_late=True,               # ack only after task completes (safe retry on crash)
    worker_prefetch_multiplier=1,      # fair dispatch — one task at a time per worker slot
    task_reject_on_worker_lost=True,   # re-queue on abrupt worker death

    # ── Time limits ───────────────────────────────────────────────────────────
    # A stalled async event loop, DB session, or provider call must not hang
    # the worker forever.  Soft limit sends SIGTERM (task can clean up);
    # hard limit sends SIGKILL after an additional 30 s grace period.
    task_soft_time_limit=120,          # SIGTERM after 2 min  (all tasks)
    task_time_limit=150,               # SIGKILL after 2.5 min (all tasks)

    # ── Memory hygiene ────────────────────────────────────────────────────────
    # Async event loops (new_event_loop per task) accumulate memory across
    # many task runs.  Recycling the worker process every N tasks prevents
    # gradual OOM on long-running workers.
    worker_max_tasks_per_child=200,

    # ── Task routing ──────────────────────────────────────────────────────────
    task_routes={
        "tasks.fraud_tasks.score_behavioral_ml":         {"queue": "fraud_high"},
        "tasks.fraud_tasks.analyze_duplicate_graph":     {"queue": "fraud_high"},
        "tasks.fraud_tasks.cleanup_expired_verifications": {"queue": "maintenance"},
        "tasks.fraud_tasks.recheck_warn_accounts":       {"queue": "maintenance"},
    },

    # ── Beat schedule ─────────────────────────────────────────────────────────
    beat_schedule={
        "cleanup-expired-verifications-daily": {
            "task":     "tasks.fraud_tasks.cleanup_expired_verifications",
            "schedule": crontab(hour=3, minute=0),    # 03:00 UTC daily
        },
        "recheck-warn-accounts-hourly": {
            "task":     "tasks.fraud_tasks.recheck_warn_accounts",
            "schedule": crontab(minute=0),            # every hour :00
        },
    },
)
