"""services/verification_service.py — Staff verification logic."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import VerificationEventNotFoundError
from events.producer import StaffProducer
from models.staff_verification import StaffVerificationEvent
from repositories.staff_profile_repository import StaffProfileRepository
from repositories.staff_verification_repository import StaffVerificationRepository
from schemas.staff_profile import StaffPublicOut
from schemas.staff_verification import VerifyResponse

log = structlog.get_logger(__name__)

_RESULT_MESSAGES = {
    "VALID": "Staff identity verified successfully.",
    "INVALID": "No staff member found with this code.",
    "SUSPENDED": "This staff member is currently suspended.",
    "TERMINATED": "This staff member is no longer active.",
    "ON_LEAVE": "This staff member is currently on leave.",
}


class VerificationService:
    def __init__(self, db: AsyncSession, producer: StaffProducer) -> None:
        self.db = db
        self.profile_repo = StaffProfileRepository(db)
        self.verification_repo = StaffVerificationRepository(db)
        self.producer = producer

    async def verify(
        self,
        code: str,
        scanner_lat: Optional[float],
        scanner_lng: Optional[float],
        scanner_ip: Optional[str],
        user_agent: Optional[str],
    ) -> VerifyResponse:
        code = code.strip()

        # Lookup staff by staff_code (case-insensitive, any org)
        profile = await self.profile_repo.get_by_code_any_org(code)

        if profile is None:
            result = "INVALID"
            staff_id = None
            org_id = None
        elif profile.status == "ACTIVE":
            result = "VALID"
            staff_id = profile.id
            org_id = profile.org_id
        elif profile.status == "SUSPENDED":
            result = "SUSPENDED"
            staff_id = profile.id
            org_id = profile.org_id
        elif profile.status == "TERMINATED":
            result = "TERMINATED"
            staff_id = profile.id
            org_id = profile.org_id
        elif profile.status == "ON_LEAVE":
            result = "ON_LEAVE"
            staff_id = profile.id
            org_id = profile.org_id
        else:
            result = "INVALID"
            staff_id = None
            org_id = None

        # Always record verification event
        event = StaffVerificationEvent(
            lookup_code=code,
            staff_id=staff_id,
            org_id=org_id,
            result=result,
            scanner_lat=scanner_lat,
            scanner_lng=scanner_lng,
            scanner_ip=scanner_ip,
            user_agent=user_agent,
        )
        event = await self.verification_repo.create(event)

        # Emit Kafka event for VALID verifications
        if result == "VALID" and profile is not None:
            self.producer.staff_verified(profile.id, profile.org_id, event.id)

        # Build public staff out
        staff_public: Optional[StaffPublicOut] = None
        if result == "VALID" and profile is not None:
            hire_year = profile.hire_date.year if profile.hire_date else None
            staff_public = StaffPublicOut(
                staff_code=profile.staff_code,
                display_name=profile.display_name,
                position=profile.position,
                department=profile.department,
                branch_name=profile.branch_name,
                employment_type=profile.employment_type,
                is_verified=profile.is_verified,
                photo_url=profile.photo_url,
                org_id=profile.org_id,
                expertise=profile.expertise,
                hire_year=hire_year,
            )

        feedback_url = (
            f"/api/v1/staff/feedback?verification_event_id={event.id}"
            if result == "VALID"
            else None
        )

        log.info("staff.verification", code=code, result=result, event_id=str(event.id))

        return VerifyResponse(
            result=result,
            verification_event_id=event.id,
            staff=staff_public,
            message=_RESULT_MESSAGES.get(result, "Verification complete."),
            feedback_url=feedback_url,
        )

    async def get_event(self, event_id: UUID) -> StaffVerificationEvent:
        event = await self.verification_repo.get_by_id(event_id)
        if not event:
            raise VerificationEventNotFoundError()
        return event
