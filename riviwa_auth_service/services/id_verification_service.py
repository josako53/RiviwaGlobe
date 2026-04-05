"""
services/id_verification_service.py
──────────────────────────────────────────────────────────────────
Handles the full government ID verification lifecycle:
  1. initiate_for_user()  — called by registration_service on REVIEW score
  2. process_webhook()    — called by the provider webhook endpoint
  3. Internal handlers    — approve / reject / expire

Commit strategy
──────────────────────────────────────────────────────────────────
Each webhook handler owns a single commit at the end of its happy
path.  Repository methods only flush (consistent with the rest of
the service layer).

Duplicate ID detection
──────────────────────────────────────────────────────────────────
On APPROVED webhook, if the ID hash already belongs to another
approved account both accounts are banned and the event is
published before returning — no user is silently activated.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import IDAlreadyUsedError, IDVerificationFailedError
from models.fraud import IDVerification, IDVerificationStatus
from models.user import AccountStatus, User
from repositories.fraud_repository import FraudRepository
from repositories.user_repository import UserRepository
from schemas.fraud import IDVerificationWebhook
from services.id_verification_provider import VerificationSession, get_verification_provider
from workers.kafka_producer import get_kafka_producer

log = structlog.get_logger(__name__)


class IDVerificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db         = db
        self.fraud_repo = FraudRepository(db)
        self.user_repo  = UserRepository(db)
        self.provider   = get_verification_provider()

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate_for_user(
        self,
        user:       User,
        return_url: Optional[str] = None,
    ) -> VerificationSession:
        """
        Called by registration_service when the fraud score triggers REVIEW.
        Creates a provider session + IDVerification DB row (flush, no commit —
        the caller owns the commit).

        If a PENDING or PROCESSING session already exists for this user it is
        reused and its stored session_url is returned so the caller can redirect
        the user without creating a duplicate provider session.
        """
        existing = await self.fraud_repo.get_pending_verification_for_user(user.id)
        if existing:
            log.info(
                "id_verification.reusing_pending_session",
                user_id=str(user.id),
                session_id=existing.provider_session_id,
            )
            # Return the URL that was stored when the session was originally created.
            # Falls back to a sentinel only if the column is absent on older rows.
            return VerificationSession(
                provider_session_id=existing.provider_session_id,
                session_url=getattr(existing, "session_url", None) or "",
                expires_in_seconds=3600,
            )

        session    = await self.provider.create_session(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            return_url=return_url,
        )
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=session.expires_in_seconds)

        # Persist session_url so it can be returned on reuse without another
        # provider round-trip.  The IDVerification model must have a session_url
        # column (nullable TEXT).
        await self.fraud_repo.create_verification({
            "user_id":             user.id,
            "provider":            settings.ID_VERIFICATION_PROVIDER,
            "provider_session_id": session.provider_session_id,
            "session_url":         session.session_url,
            "status":              IDVerificationStatus.PENDING,
            "expires_at":          expires_at,
        })

        log.info(
            "id_verification.session_created",
            user_id=str(user.id),
            provider=settings.ID_VERIFICATION_PROVIDER,
            session_id=session.provider_session_id,
        )
        return session

    # ── Webhook processing ────────────────────────────────────────────────────

    async def process_webhook(
        self,
        raw_payload: dict,
        signature:   Optional[str] = None,
    ) -> None:
        """
        Entry point called by the webhook endpoint.

        Parses and validates the provider payload, updates DB records,
        and activates or blocks the user account.

        Silently returns (after logging) when the session_id is unknown —
        this guards against replayed or third-party events without raising.
        Raises ValueError on signature validation failure (caught by the
        endpoint and returned as 400).
        """
        # parse_webhook raises ValueError on bad signature — let it propagate.
        webhook = self.provider.parse_webhook(raw_payload, signature)

        verification = await self.fraud_repo.get_verification_by_provider_session(
            webhook.provider_session_id
        )
        if not verification:
            log.warning(
                "id_verification.webhook.unknown_session",
                session_id=webhook.provider_session_id,
            )
            return

        if webhook.status == "approved":
            await self._handle_approved(verification, webhook)
        elif webhook.status == "rejected":
            await self._handle_rejected(verification, webhook)
        elif webhook.status == "expired":
            await self._handle_expired(verification)
        else:
            log.warning(
                "id_verification.webhook.unknown_status",
                status=webhook.status,
                session_id=webhook.provider_session_id,
            )

    # ── Internal handlers ─────────────────────────────────────────────────────

    async def _handle_approved(
        self,
        verification: IDVerification,
        webhook:      IDVerificationWebhook,
    ) -> None:
        """
        Approve the verification:
          · Duplicate-ID guard: if the hash already belongs to another approved
            account, ban both accounts and publish a duplicate-detected event.
          · Otherwise: mark verification APPROVED, activate user, commit.
        """
        user = await self.user_repo.get_by_id(verification.user_id)
        if not user:
            log.error(
                "id_verification.approved.user_not_found",
                user_id=str(verification.user_id),
            )
            return

        # ── Duplicate government-ID guard ─────────────────────────────────────
        if webhook.id_number_hash:
            existing_v = await self.fraud_repo.get_verification_by_id_hash(
                webhook.id_number_hash
            )
            if existing_v and existing_v.user_id != user.id:
                log.warning(
                    "id_verification.duplicate_id_detected",
                    new_user_id=str(user.id),
                    existing_user_id=str(existing_v.user_id),
                    id_hash_prefix=webhook.id_number_hash[:8] + "...",
                )
                # Ban the new account; reject this verification attempt.
                # The existing account may also need review — ban it too and let
                # an admin investigation event drive any manual reinstatement.
                await self.user_repo.set_status(user.id, AccountStatus.BANNED)
                await self.user_repo.set_status(existing_v.user_id, AccountStatus.BANNED)
                await self.fraud_repo.update_verification(
                    verification,
                    status=IDVerificationStatus.REJECTED,
                    rejection_reason="id_already_registered",
                    completed_at=datetime.now(timezone.utc),
                )
                await self.db.commit()
                await self._publish_event("user.id_duplicate_detected", {
                    "user_id":          str(user.id),
                    "existing_user_id": str(existing_v.user_id),
                })
                return

        # ── Happy path: approve ───────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        await self.fraud_repo.update_verification(
            verification,
            status=IDVerificationStatus.APPROVED,
            id_number_hash=webhook.id_number_hash,
            id_type=webhook.id_type,
            id_country=webhook.id_country,
            name_match=webhook.name_match,
            dob_match=webhook.dob_match,
            completed_at=now,
        )
        # Use the targeted repository method — UserRepository has no generic update().
        await self.user_repo.mark_id_verified(user.id)
        await self.db.commit()

        log.info("id_verification.approved", user_id=str(user.id))
        await self._publish_event("user.id_verified", {"user_id": str(user.id)})

    async def _handle_rejected(
        self,
        verification: IDVerification,
        webhook:      IDVerificationWebhook,
        reason:       Optional[str] = None,
    ) -> None:
        """
        Mark verification REJECTED.  The user stays at PENDING_ID so they can
        retry (up to a provider-level limit).  No status change on the User row.
        """
        await self.fraud_repo.update_verification(
            verification,
            status=IDVerificationStatus.REJECTED,
            rejection_reason=reason or webhook.rejection_reason,
            completed_at=datetime.now(timezone.utc),
        )
        await self.db.commit()

        user = await self.user_repo.get_by_id(verification.user_id)
        if user:
            log.info(
                "id_verification.rejected",
                user_id=str(user.id),
                reason=reason or webhook.rejection_reason,
            )
            await self._publish_event("user.id_verification_failed", {
                "user_id": str(user.id),
                "reason":  reason or webhook.rejection_reason,
            })

    async def _handle_expired(self, verification: IDVerification) -> None:
        """Mark verification EXPIRED.  No action on the user account."""
        await self.fraud_repo.update_verification(
            verification,
            status=IDVerificationStatus.EXPIRED,
        )
        await self.db.commit()
        log.info(
            "id_verification.expired",
            session_id=verification.provider_session_id,
        )

    # ── Kafka helper ───────────────────────────────────────────────────────────

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        """
        Fire-and-forget Kafka publish.
        Failures are logged but never propagated — the webhook must still
        return 200 to prevent the provider retrying indefinitely.
        """
        try:
            producer = await get_kafka_producer()
            topic    = getattr(settings, "KAFKA_TOPIC_ID_VERIFICATION", "riviwa.id_verification.events")
            await producer.publish(
                topic=topic,
                key=payload.get("user_id", "unknown"),
                value={
                    "event":     event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **payload,
                },
            )
        except Exception as exc:
            log.warning(
                "id_verification.kafka_publish_failed",
                event=event_type,
                error=str(exc),
            )
