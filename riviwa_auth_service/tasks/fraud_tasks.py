"""
tasks/fraud_tasks.py
──────────────────────────────────────────────────────────────────
Celery tasks for async fraud analysis:

  score_behavioral_ml           — run heuristic / ML model on behavioral session
  analyze_duplicate_graph       — graph-walk linked accounts
  cleanup_expired_verifications — daily: expire stale ID sessions + reset tokens
  recheck_warn_accounts         — hourly: re-score WARN-flagged accounts

Async pattern
──────────────────────────────────────────────────────────────────
Celery workers are synchronous; each task creates a fresh event loop
via asyncio.new_event_loop() to run the async DB/Redis work.
AsyncSessionLocal is used (not the request-scoped DI session) because
these tasks execute outside any HTTP request context.

All tasks use bind=True so self.retry() is available, and
task_acks_late=True (set in celery_app.py) ensures a task is
re-queued if the worker process dies mid-execution.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

from workers.celery_app import celery_app

log = structlog.get_logger(__name__)


# ── Async bridge ───────────────────────────────────────────────────────────────

def _run_async(coro):
    """
    Run an async coroutine to completion inside a Celery (sync) task.
    A new event loop is created per call and closed immediately after,
    preventing loop-state leakage between tasks and across worker_max_tasks_per_child
    restarts.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── score_behavioral_ml ────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.fraud_tasks.score_behavioral_ml",
    max_retries=3,
    default_retry_delay=30,
)
def score_behavioral_ml(self, session_token: str, user_id: str) -> dict:
    """
    Run the heuristic behavioral model on a completed registration session.
    Updates BehavioralSession.ml_bot_probability + behavioral_score.
    If the ML score is >= 80, the user is escalated to PENDING_ID.
    """
    try:
        return _run_async(_score_behavioral_ml_async(session_token, user_id))
    except Exception as exc:
        log.error("fraud_tasks.score_behavioral_ml.failed", error=str(exc), user_id=user_id)
        raise self.retry(exc=exc)


async def _score_behavioral_ml_async(session_token: str, user_id: str) -> dict:
    from db.session import AsyncSessionLocal
    from models.user_role import AccountStatus
    from repositories.fraud_repository import FraudRepository
    from repositories.user_repository import UserRepository

    async with AsyncSessionLocal() as db:
        fraud_repo = FraudRepository(db)
        user_repo  = UserRepository(db)

        session = await fraud_repo.get_session_by_token(session_token)
        if not session:
            log.warning(
                "fraud_tasks.behavioral_session_not_found",
                token=session_token[:12] + "...",
            )
            return {"status": "session_not_found"}

        bot_probability  = _compute_bot_probability(session)
        behavioral_score = int(bot_probability * 100)

        await fraud_repo.update_behavioral_session(
            session,
            ml_bot_probability=bot_probability,
            behavioral_score=behavioral_score,
            scored_at=datetime.now(timezone.utc),
        )

        # Escalate to manual ID review when score is very high and the
        # account is already ACTIVE (i.e. it passed the real-time gate but
        # the async model disagrees).
        if behavioral_score >= 80 and user_id:
            uid  = uuid.UUID(user_id)
            user = await user_repo.get_by_id(uid)
            if user and user.status == AccountStatus.ACTIVE:
                # Use the targeted repository method — UserRepository has no
                # generic update(); calling a non-existent method raises
                # AttributeError at runtime.
                await user_repo.set_status(uid, AccountStatus.PENDING_ID)
                log.warning(
                    "fraud_tasks.behavioral_escalation",
                    user_id=user_id,
                    bot_probability=bot_probability,
                )

        await db.commit()
        return {
            "status":          "scored",
            "bot_probability": bot_probability,
            "score":           behavioral_score,
        }


def _compute_bot_probability(session) -> float:
    """
    Heuristic model.  Replace with a trained scikit-learn / XGBoost model
    on labeled bot vs. human session data in production.
    Features are ordered from highest to lowest discriminative power.
    """
    score = 0.0

    if getattr(session, "form_time_seconds", None) and session.form_time_seconds < 3:
        score += 0.5          # sub-3 s form completion — almost always a bot
    if getattr(session, "rapid_completion", False):
        score += 0.6
    if getattr(session, "paste_detected", False) and not getattr(session, "mouse_movement_count", 1):
        score += 0.4          # paste + zero mouse → scripted
    if (
        not getattr(session, "mouse_movement_count", 1)
        and not getattr(session, "touch_device", False)
    ):
        score += 0.3          # no mouse on a desktop browser
    if getattr(session, "typing_speed_avg_ms", None) and session.typing_speed_avg_ms < 30:
        score += 0.3          # <30 ms between keystrokes is physically impossible
    if getattr(session, "devtools_opened", False):
        score += 0.2
    if getattr(session, "tab_hidden_count", 0) > 5:
        score += 0.1

    return min(score, 1.0)


# ── analyze_duplicate_graph ────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.fraud_tasks.analyze_duplicate_graph",
    max_retries=2,
    default_retry_delay=60,
)
def analyze_duplicate_graph(self, user_id: str) -> dict:
    """
    Walk the graph of linked accounts (shared IP, fingerprint) and log
    connection density for downstream risk scoring / manual review.
    """
    try:
        return _run_async(_analyze_duplicate_graph_async(user_id))
    except Exception as exc:
        log.error(
            "fraud_tasks.analyze_duplicate_graph.failed",
            error=str(exc),
            user_id=user_id,
        )
        raise self.retry(exc=exc)


async def _analyze_duplicate_graph_async(user_id: str) -> dict:
    from sqlalchemy import select

    from db.session import AsyncSessionLocal
    from models.fraud import DeviceFingerprint
    from repositories.fraud_repository import FraudRepository

    async with AsyncSessionLocal() as db:
        fraud_repo = FraudRepository(db)
        uid        = uuid.UUID(user_id)

        # Find all fingerprint records belonging to this user.
        result = await db.execute(
            select(DeviceFingerprint).where(DeviceFingerprint.user_id == uid)
        )
        fp_records = list(result.scalars().all())

        linked_user_ids: set[str] = set()
        for fp in fp_records:
            linked = await fraud_repo.get_users_by_fingerprint(fp.fingerprint_hash)
            linked_user_ids.update(str(u) for u in linked if u != uid)

        if linked_user_ids:
            log.warning(
                "fraud_tasks.duplicate_graph.links_found",
                user_id=user_id,
                linked_count=len(linked_user_ids),
                linked_ids=list(linked_user_ids)[:10],   # cap log size
            )

        await db.commit()
        return {"user_id": user_id, "linked_accounts": list(linked_user_ids)}


# ── cleanup_expired_verifications ─────────────────────────────────────────────

@celery_app.task(name="tasks.fraud_tasks.cleanup_expired_verifications")
def cleanup_expired_verifications() -> dict:
    """
    Daily maintenance task (03:00 UTC via beat):
      1. Bulk-expire PENDING/PROCESSING IDVerification rows past their
         expires_at deadline.
      2. Bulk-invalidate used/expired PasswordResetToken rows older than
         30 days (housekeeping — they are already logically consumed).
    """
    return _run_async(_cleanup_async())


async def _cleanup_async() -> dict:
    from sqlalchemy import and_, update

    from db.session import AsyncSessionLocal
    from models.fraud import IDVerification, IDVerificationStatus
    from models.password_reset import PasswordResetToken

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # ── 1. Expire stale ID verification sessions ──────────────────────────
        result = await db.execute(
            update(IDVerification)
            .where(
                and_(
                    IDVerification.status.in_([
                        IDVerificationStatus.PENDING,
                        IDVerificationStatus.PROCESSING,
                    ]),
                    IDVerification.expires_at < now,
                )
            )
            .values(status=IDVerificationStatus.EXPIRED)
        )
        expired_verifications = result.rowcount

        # ── 2. Hard-delete PasswordResetToken rows consumed > 30 days ago ─────
        # These are already logically inactive (used_at IS NOT NULL or
        # expires_at in the past).  Removing them keeps the table small.
        cutoff_30d = now - timedelta(days=30)
        from sqlalchemy import delete as sa_delete
        del_result = await db.execute(
            sa_delete(PasswordResetToken).where(
                PasswordResetToken.expires_at < cutoff_30d,
            )
        )
        cleaned_tokens = del_result.rowcount

        await db.commit()

    log.info(
        "fraud_tasks.cleanup_complete",
        expired_verifications=expired_verifications,
        cleaned_tokens=cleaned_tokens,
    )
    return {
        "expired_verifications": expired_verifications,
        "cleaned_tokens":        cleaned_tokens,
    }


# ── recheck_warn_accounts ──────────────────────────────────────────────────────

@celery_app.task(name="tasks.fraud_tasks.recheck_warn_accounts")
def recheck_warn_accounts() -> dict:
    """
    Hourly beat task: surface WARN-flagged accounts from the last 7 days
    for downstream review or automated re-scoring pipeline.

    Currently logs the count and returns assessment IDs for the caller
    (e.g. a future ML re-scoring pipeline) to act on.  Replace the body
    with a real escalation or re-scoring pass once the ML model is live.
    """
    return _run_async(_recheck_warn_async())


async def _recheck_warn_async() -> dict:
    from sqlalchemy import select

    from db.session import AsyncSessionLocal
    from models.fraud import FraudAction, FraudAssessment

    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(FraudAssessment)
            .where(
                FraudAssessment.action == FraudAction.WARN,
                FraudAssessment.created_at >= cutoff,
                FraudAssessment.user_id.is_not(None),
            )
            .order_by(FraudAssessment.created_at.desc())
            .limit(100)
        )
        assessments = list(result.scalars().all())

        log.info("fraud_tasks.recheck_warn", count=len(assessments))
        # Future: for each assessment, re-run ScoringEngine with fresh signals
        # and escalate to REVIEW/BLOCK if score has risen.

        await db.commit()

    return {
        "rechecked":      len(assessments),
        "assessment_ids": [str(a.id) for a in assessments],
    }
