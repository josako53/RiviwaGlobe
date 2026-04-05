"""
repositories/fraud_repository.py
──────────────────────────────────────────────────────────────────
All DB operations for the five fraud tables:
  DeviceFingerprint, IPRecord, FraudAssessment,
  IDVerification, BehavioralSession

Design rules (same as UserRepository / OrganisationRepository)
──────────────────────────────────────────────────────────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found rows.
  · flush() only — commit is owned by the service layer.
  · update_assessment / update_verification accept only an explicit
    allowlist of columns; unknown keys are silently ignored.
  · seen_count increment is done via a SQL expression (atomic).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.fraud import (
    BehavioralSession,
    DeviceFingerprint,
    FraudAction,
    FraudAssessment,
    IDVerification,
    IDVerificationStatus,
    IPRecord,
)

log = structlog.get_logger(__name__)

# Allowlisted columns for generic update helpers — prevents arbitrary column writes.
_ASSESSMENT_UPDATABLE: frozenset[str] = frozenset({
    "id_verification_id",
    "action", "action_reason",
    "score_email", "score_ip", "score_fingerprint",
    "score_behavioral", "score_velocity", "score_geo",
    "total_score", "signal_details", "linked_account_ids",
})

_VERIFICATION_UPDATABLE: frozenset[str] = frozenset({
    "status", "id_number_hash", "id_type", "id_country",
    "name_match", "dob_match", "rejection_reason",
    "completed_at", "expires_at",
})


class FraudRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── DeviceFingerprint ──────────────────────────────────────────────────────

    async def get_fingerprint(self, fingerprint_hash: str) -> list[DeviceFingerprint]:
        """Return all records matching this hash (multiple users → duplicate signal)."""
        result = await self.db.execute(
            select(DeviceFingerprint).where(
                DeviceFingerprint.fingerprint_hash == fingerprint_hash
            )
        )
        return list(result.scalars().all())

    async def upsert_fingerprint(
        self, user_id: uuid.UUID, data: dict
    ) -> DeviceFingerprint:
        """
        Create or update fingerprint record for this user+hash combo.

        seen_count is incremented atomically via a targeted UPDATE rather
        than a read-modify-write in Python to avoid races under concurrent
        registrations from the same device.
        """
        fingerprint_hash = data["fingerprint_hash"]
        existing = await self.db.execute(
            select(DeviceFingerprint).where(
                and_(
                    DeviceFingerprint.user_id == user_id,
                    DeviceFingerprint.fingerprint_hash == fingerprint_hash,
                )
            )
        )
        fp = existing.scalar_one_or_none()

        if fp:
            # Atomic increment — avoids read-modify-write race
            await self.db.execute(
                update(DeviceFingerprint)
                .where(DeviceFingerprint.id == fp.id)
                .values(
                    seen_count=DeviceFingerprint.seen_count + 1,
                    last_seen=datetime.now(timezone.utc),
                )
            )
            await self.db.refresh(fp)
        else:
            fp = DeviceFingerprint(user_id=user_id, **data)
            self.db.add(fp)

        await self.db.flush()
        log.debug(
            "fraud.fingerprint_upserted",
            user_id=str(user_id),
            fp_hash=fingerprint_hash[:12] + "...",
        )
        return fp

    async def get_users_by_fingerprint(self, fingerprint_hash: str) -> list[uuid.UUID]:
        """Return distinct user_ids that have used this fingerprint."""
        result = await self.db.execute(
            select(DeviceFingerprint.user_id).where(
                DeviceFingerprint.fingerprint_hash == fingerprint_hash
            ).distinct()
        )
        return list(result.scalars().all())

    # ── IPRecord ───────────────────────────────────────────────────────────────

    async def get_users_by_ip(self, ip_address: str) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(IPRecord.user_id).where(
                IPRecord.ip_address == ip_address
            ).distinct()
        )
        return list(result.scalars().all())

    async def create_ip_record(self, user_id: uuid.UUID, data: dict) -> IPRecord:
        record = IPRecord(user_id=user_id, **data)
        self.db.add(record)
        await self.db.flush()
        log.debug("fraud.ip_record_created", user_id=str(user_id), ip=data.get("ip_address"))
        return record

    async def get_ip_record_for_user(
        self, user_id: uuid.UUID, ip_address: str
    ) -> Optional[IPRecord]:
        result = await self.db.execute(
            select(IPRecord).where(
                and_(
                    IPRecord.user_id == user_id,
                    IPRecord.ip_address == ip_address,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── FraudAssessment ────────────────────────────────────────────────────────

    async def create_assessment(self, data: dict) -> FraudAssessment:
        assessment = FraudAssessment(**data)
        self.db.add(assessment)
        await self.db.flush()
        await self.db.refresh(assessment)
        log.debug(
            "fraud.assessment_created",
            assessment_id=str(assessment.id),
            user_id=str(data.get("user_id")),
            total_score=data.get("total_score"),
        )
        return assessment

    async def get_assessment(
        self, assessment_id: uuid.UUID
    ) -> Optional[FraudAssessment]:
        result = await self.db.execute(
            select(FraudAssessment).where(FraudAssessment.id == assessment_id)
        )
        return result.scalar_one_or_none()

    async def list_assessments_for_user(
        self, user_id: uuid.UUID
    ) -> list[FraudAssessment]:
        result = await self.db.execute(
            select(FraudAssessment)
            .where(FraudAssessment.user_id == user_id)
            .order_by(FraudAssessment.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_assessment(
        self, assessment: FraudAssessment, **kwargs
    ) -> FraudAssessment:
        """
        Update allowed FraudAssessment fields only.
        Unknown keys are silently dropped to prevent arbitrary column writes.
        Allowed: id_verification_id, action, action_reason, score_*, total_score,
                 signal_details, linked_account_ids.
        """
        safe = {k: v for k, v in kwargs.items() if k in _ASSESSMENT_UPDATABLE}
        for key, value in safe.items():
            setattr(assessment, key, value)
        await self.db.flush()
        return assessment

    # ── IDVerification ─────────────────────────────────────────────────────────

    async def create_verification(self, data: dict) -> IDVerification:
        v = IDVerification(**data)
        self.db.add(v)
        await self.db.flush()
        await self.db.refresh(v)
        log.debug(
            "fraud.verification_created",
            verification_id=str(v.id),
            user_id=str(data.get("user_id")),
            provider=data.get("provider"),
        )
        return v

    async def get_verification_by_id(
        self, verification_id: uuid.UUID
    ) -> Optional[IDVerification]:
        result = await self.db.execute(
            select(IDVerification).where(IDVerification.id == verification_id)
        )
        return result.scalar_one_or_none()

    async def get_verification_by_provider_session(
        self, provider_session_id: str
    ) -> Optional[IDVerification]:
        result = await self.db.execute(
            select(IDVerification).where(
                IDVerification.provider_session_id == provider_session_id
            )
        )
        return result.scalar_one_or_none()

    async def get_verification_by_id_hash(
        self, id_number_hash: str
    ) -> Optional[IDVerification]:
        """
        Check if this government ID hash already exists in an APPROVED row.
        Used as a permanent duplicate-identity guard.
        """
        result = await self.db.execute(
            select(IDVerification).where(
                and_(
                    IDVerification.id_number_hash == id_number_hash,
                    IDVerification.status == IDVerificationStatus.APPROVED,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_verification(
        self, verification: IDVerification, **kwargs
    ) -> IDVerification:
        """
        Update allowed IDVerification fields only.
        Unknown keys are silently dropped to prevent arbitrary column writes.
        Allowed: status, id_number_hash, id_type, id_country, name_match,
                 dob_match, rejection_reason, completed_at, expires_at.
        Always stamps updated_at = now().
        """
        safe = {k: v for k, v in kwargs.items() if k in _VERIFICATION_UPDATABLE}
        for key, value in safe.items():
            setattr(verification, key, value)
        verification.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return verification

    async def get_pending_verification_for_user(
        self, user_id: uuid.UUID
    ) -> Optional[IDVerification]:
        """
        Return the most recent PENDING or PROCESSING verification row for a user.

        .limit(1) is required — scalar_one_or_none() raises MultipleResultsFound
        if the user has more than one in-flight row (e.g. after a retry).
        """
        result = await self.db.execute(
            select(IDVerification)
            .where(
                and_(
                    IDVerification.user_id == user_id,
                    IDVerification.status.in_([
                        IDVerificationStatus.PENDING,
                        IDVerificationStatus.PROCESSING,
                    ]),
                )
            )
            .order_by(IDVerification.created_at.desc())
            .limit(1)                          # ← required: prevents MultipleResultsFound
        )
        return result.scalar_one_or_none()

    # ── BehavioralSession ──────────────────────────────────────────────────────

    async def get_session_by_token(
        self, session_token: str
    ) -> Optional[BehavioralSession]:
        result = await self.db.execute(
            select(BehavioralSession).where(
                BehavioralSession.session_token == session_token
            )
        )
        return result.scalar_one_or_none()

    async def create_behavioral_session(self, data: dict) -> BehavioralSession:
        session = BehavioralSession(**data)
        self.db.add(session)
        await self.db.flush()
        log.debug("fraud.behavioral_session_created")
        return session

    async def update_behavioral_session(
        self, session: BehavioralSession, **kwargs
    ) -> BehavioralSession:
        for key, value in kwargs.items():
            setattr(session, key, value)
        await self.db.flush()
        return session
