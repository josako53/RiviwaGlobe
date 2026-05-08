"""services/staff_service.py — Core staff profile business logic."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ForbiddenError,
    OrgInactiveError,
    OrgNotFoundError,
    StaffAlreadySuspendedError,
    StaffAlreadyTerminatedError,
    StaffNotFoundError,
    StaffNotSuspendedError,
)
from events.producer import StaffProducer
from models.staff_profile import StaffProfile
from repositories.org_cache_repository import OrgCacheRepository
from repositories.staff_profile_repository import StaffProfileRepository
from schemas.staff_profile import StaffProfileCreate, StaffProfileUpdate

log = structlog.get_logger(__name__)


def _format_staff_code(slug: Optional[str], seq: int) -> str:
    """Format staff code as {ORG_SLUG_UPPER}-{SEQ:05d}, e.g. MNH-00042."""
    prefix = (slug or "ORG").upper()[:6]  # Cap prefix at 6 chars
    return f"{prefix}-{seq:05d}"


class StaffService:
    def __init__(self, db: AsyncSession, producer: StaffProducer) -> None:
        self.db = db
        self.repo = StaffProfileRepository(db)
        self.org_repo = OrgCacheRepository(db)
        self.producer = producer

    async def _assert_org(self, org_id: UUID) -> Any:
        org = await self.org_repo.get(org_id)
        if not org:
            raise OrgNotFoundError(detail={"org_id": str(org_id)})
        if not org.is_active:
            raise OrgInactiveError(detail={"org_id": str(org_id)})
        return org

    async def create_profile(
        self,
        org_id: UUID,
        data: StaffProfileCreate,
        created_by: Optional[str] = None,
    ) -> StaffProfile:
        org = await self._assert_org(org_id)

        # Generate staff code
        seq = await self.repo.next_sequence(org_id)
        staff_code = _format_staff_code(org.slug, seq)

        # Build display_name
        display_name = data.display_name
        if not display_name:
            parts = [data.first_name]
            if data.middle_name:
                parts.append(data.middle_name)
            parts.append(data.last_name)
            display_name = " ".join(parts)

        raw = data.model_dump(exclude={"display_name", "metadata_"})
        # Handle metadata_ alias
        metadata_val = None
        if data.metadata_ is not None:
            metadata_val = data.metadata_

        # Convert project_ids to list of str for JSONB
        project_ids = None
        if raw.get("project_ids"):
            project_ids = [str(pid) for pid in raw["project_ids"]]

        profile = StaffProfile(
            org_id=org_id,
            staff_code=staff_code,
            display_name=display_name,
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
            badge_number=data.badge_number,
            phone=data.phone,
            email=data.email,
            position=data.position,
            department=data.department,
            branch_id=data.branch_id,
            branch_name=data.branch_name,
            supervisor_id=data.supervisor_id,
            employment_type=data.employment_type.upper(),
            expertise=data.expertise,
            bio=data.bio,
            id_number=data.id_number,
            project_ids=project_ids,
            metadata_=metadata_val,
            hire_date=data.hire_date,
            qr_code_id=data.qr_code_id,
            created_by=UUID(created_by) if created_by else None,
            status="ACTIVE",
        )
        profile = await self.repo.create(profile)

        self.producer.profile_created(profile.id, org_id, staff_code, created_by)
        log.info("staff.profile.created", staff_id=str(profile.id), org_id=str(org_id))
        return profile

    async def get_profile(self, profile_id: UUID, org_id: UUID, is_platform_admin: bool = False) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        return profile

    async def list_profiles(
        self,
        org_id: UUID,
        department: Optional[str] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[str] = None,
        position: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffProfile], int]:
        return await self.repo.list_by_org(
            org_id, department, branch_id, status, position, page, size
        )

    async def update_profile(
        self,
        profile_id: UUID,
        org_id: UUID,
        data: StaffProfileUpdate,
        is_platform_admin: bool = False,
    ) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()

        updates = data.model_dump(exclude_unset=True)
        # Handle display_name recompute if names changed
        if any(k in updates for k in ("first_name", "last_name", "middle_name")) and "display_name" not in updates:
            first = updates.get("first_name", profile.first_name)
            middle = updates.get("middle_name", profile.middle_name)
            last = updates.get("last_name", profile.last_name)
            parts = [first]
            if middle:
                parts.append(middle)
            parts.append(last)
            updates["display_name"] = " ".join(parts)

        if "employment_type" in updates and updates["employment_type"]:
            updates["employment_type"] = updates["employment_type"].upper()

        # Handle metadata_ alias
        if "metadata_" in updates:
            updates["metadata_"] = updates.pop("metadata_")

        profile = await self.repo.update(profile, updates)
        self.producer.profile_updated(profile.id, org_id)
        return profile

    async def soft_delete(
        self, profile_id: UUID, org_id: UUID, reason: str = "Profile deleted", is_platform_admin: bool = False
    ) -> None:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        await self.repo.update(profile, {"status": "TERMINATED", "termination_reason": reason})
        self.producer.profile_terminated(profile.id, org_id, reason)

    async def suspend(
        self, profile_id: UUID, org_id: UUID, reason: str, is_platform_admin: bool = False
    ) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        if profile.status == "SUSPENDED":
            raise StaffAlreadySuspendedError()
        if profile.status == "TERMINATED":
            raise StaffAlreadyTerminatedError()
        profile = await self.repo.update(profile, {"status": "SUSPENDED", "suspension_reason": reason})
        self.producer.profile_suspended(profile.id, org_id, reason)
        return profile

    async def reinstate(
        self, profile_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        if profile.status != "SUSPENDED":
            raise StaffNotSuspendedError()
        profile = await self.repo.update(profile, {
            "status": "ACTIVE",
            "suspension_reason": None,
        })
        self.producer.profile_updated(profile.id, org_id)
        return profile

    async def terminate(
        self, profile_id: UUID, org_id: UUID, reason: str, is_platform_admin: bool = False
    ) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        if profile.status == "TERMINATED":
            raise StaffAlreadyTerminatedError()
        profile = await self.repo.update(profile, {
            "status": "TERMINATED",
            "termination_reason": reason,
        })
        self.producer.profile_terminated(profile.id, org_id, reason)
        return profile

    async def verify_profile(
        self, profile_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> StaffProfile:
        """Mark a staff profile as org-verified."""
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        profile = await self.repo.update(profile, {"is_verified": True})
        self.producer.profile_updated(profile.id, org_id)
        return profile

    async def set_photo(
        self, profile_id: UUID, org_id: UUID, photo_key: str, photo_url: str,
        is_platform_admin: bool = False,
    ) -> StaffProfile:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            raise StaffNotFoundError()
        if not is_platform_admin and profile.org_id != org_id:
            raise ForbiddenError()
        profile = await self.repo.update(profile, {"photo_key": photo_key, "photo_url": photo_url})
        return profile

    async def get_profile_with_stats(
        self, profile_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> Dict[str, Any]:
        profile = await self.get_profile(profile_id, org_id, is_platform_admin)
        stats = await self.repo.feedback_stats(profile_id)
        return {"profile": profile, **stats}
