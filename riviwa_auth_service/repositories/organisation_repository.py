# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/organisation_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/organisation_repository.py
═══════════════════════════════════════════════════════════════════════════════
All DB operations for the three organisation tables:

  Organisation         — the registered entity
  OrganisationMember   — (User ↔ Org) with role + status
  OrganisationInvite   — pending invitations

Design rules  (same as UserRepository)
──────────────────────────────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found rows.
  · Uses flush() only — commit is owned by the service layer.
  · Targeted UPDATE() statements for performance.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.organisation import (
    OrgInviteStatus,
    OrgMemberRole,
    OrgMemberStatus,
    OrgStatus,
    OrgType,
    Organisation,
    OrganisationInvite,
    OrganisationMember,
)

log = structlog.get_logger(__name__)


class OrganisationRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Organisation lookups ──────────────────────────────────────────────────

    async def get_by_id(self, org_id: uuid.UUID) -> Optional[Organisation]:
        result = await self.db.execute(
            select(Organisation).where(Organisation.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Organisation]:
        result = await self.db.execute(
            select(Organisation).where(Organisation.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(Organisation.id).where(Organisation.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def list_by_creator(self, user_id: uuid.UUID) -> list[Organisation]:
        result = await self.db.execute(
            select(Organisation)
            .where(Organisation.created_by_id == user_id)
            .order_by(Organisation.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Organisation create / update ──────────────────────────────────────────

    async def create(
        self,
        *,
        legal_name:          str,
        display_name:        str,
        slug:                str,
        org_type:            OrgType,
        created_by_id:       uuid.UUID,
        description:         Optional[str]  = None,
        logo_url:            Optional[str]  = None,
        website_url:         Optional[str]  = None,
        support_email:       Optional[str]  = None,
        support_phone:       Optional[str]  = None,
        country_code:        Optional[str]  = None,
        timezone:            Optional[str]  = None,
        registration_number: Optional[str]  = None,
        tax_id:              Optional[str]  = None,
        max_members:         int            = 0,
    ) -> Organisation:
        """
        INSERT a new Organisation row (status=PENDING_VERIFICATION, is_verified=False).
        Flushes but does NOT commit.
        """
        org = Organisation(
            legal_name=legal_name,
            display_name=display_name,
            slug=slug,
            org_type=org_type,
            created_by_id=created_by_id,
            status=OrgStatus.PENDING_VERIFICATION,
            is_verified=False,
            description=description,
            logo_url=logo_url,
            website_url=website_url,
            support_email=support_email,
            support_phone=support_phone,
            country_code=country_code,
            timezone=timezone,
            registration_number=registration_number,
            tax_id=tax_id,
            max_members=max_members,
        )
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        log.debug("organisation.created", org_id=str(org.id), slug=slug)
        return org

    async def update(
        self,
        org: Organisation,
        **fields,
    ) -> Organisation:
        """
        Generic update of allowed Organisation fields.
        Accepted: legal_name, display_name, slug, description, logo_url,
                  website_url, support_email, support_phone, country_code,
                  timezone, registration_number, tax_id, max_members.
        """
        allowed = {
            "legal_name", "display_name", "slug", "description", "logo_url",
            "website_url", "support_email", "support_phone", "country_code",
            "timezone", "registration_number", "tax_id", "max_members",
        }
        for k, v in fields.items():
            if k in allowed:
                setattr(org, k, v)
        await self.db.flush()
        return org

    async def verify(
        self,
        org:            Organisation,
        verified_by_id: uuid.UUID,
    ) -> Organisation:
        """
        Platform admin approval: is_verified=True, status=ACTIVE, verified_at=now().
        """
        now = datetime.now(timezone.utc)
        org.is_verified    = True
        org.verified_at    = now
        org.verified_by_id = verified_by_id
        org.status         = OrgStatus.ACTIVE
        await self.db.flush()
        return org

    async def set_status(
        self,
        org_id: uuid.UUID,
        status: OrgStatus,
    ) -> None:
        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(status=status)
        )
        await self.db.flush()

    async def soft_delete(self, org_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(status=OrgStatus.DEACTIVATED, deleted_at=now)
        )
        await self.db.flush()

    # ── OrganisationMember lookups ────────────────────────────────────────────

    async def get_member(
        self,
        org_id:  uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OrganisationMember]:
        """Return the membership row for any status."""
        result = await self.db.execute(
            select(OrganisationMember).where(
                and_(
                    OrganisationMember.organisation_id == org_id,
                    OrganisationMember.user_id         == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_member(
        self,
        org_id:  uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OrganisationMember]:
        """Return the membership row only if status == ACTIVE."""
        result = await self.db.execute(
            select(OrganisationMember).where(
                and_(
                    OrganisationMember.organisation_id == org_id,
                    OrganisationMember.user_id         == user_id,
                    OrganisationMember.status          == OrgMemberStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self,
        org_id: uuid.UUID,
    ) -> list[OrganisationMember]:
        result = await self.db.execute(
            select(OrganisationMember)
            .where(OrganisationMember.organisation_id == org_id)
            .order_by(OrganisationMember.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_active_members(
        self,
        org_id: uuid.UUID,
    ) -> list[OrganisationMember]:
        result = await self.db.execute(
            select(OrganisationMember).where(
                and_(
                    OrganisationMember.organisation_id == org_id,
                    OrganisationMember.status          == OrgMemberStatus.ACTIVE,
                )
            ).order_by(OrganisationMember.joined_at.asc())
        )
        return list(result.scalars().all())

    async def count_active_members(self, org_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(OrganisationMember).where(
                and_(
                    OrganisationMember.organisation_id == org_id,
                    OrganisationMember.status          == OrgMemberStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one()

    async def list_memberships_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[OrganisationMember]:
        """All org memberships for a single user (all statuses)."""
        result = await self.db.execute(
            select(OrganisationMember)
            .where(OrganisationMember.user_id == user_id)
            .order_by(OrganisationMember.created_at.asc())
        )
        return list(result.scalars().all())

    # ── OrganisationMember create / update ────────────────────────────────────

    async def add_member(
        self,
        org_id:        uuid.UUID,
        user_id:       uuid.UUID,
        org_role:      OrgMemberRole,
        *,
        invited_by_id: Optional[uuid.UUID] = None,
        status:        OrgMemberStatus     = OrgMemberStatus.ACTIVE,
    ) -> OrganisationMember:
        """
        INSERT an OrganisationMember row and flush.
        joined_at is set to now() when status=ACTIVE (direct add / invite accept).
        """
        now = datetime.now(timezone.utc)
        member = OrganisationMember(
            organisation_id=org_id,
            user_id=user_id,
            org_role=org_role,
            status=status,
            invited_by_id=invited_by_id,
            joined_at=now if status == OrgMemberStatus.ACTIVE else None,
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        log.debug(
            "org_member.added",
            org_id=str(org_id),
            user_id=str(user_id),
            role=org_role.value,
        )
        return member

    async def update_member_role(
        self,
        member:   OrganisationMember,
        new_role: OrgMemberRole,
    ) -> OrganisationMember:
        member.org_role = new_role
        await self.db.flush()
        return member

    async def update_member_status(
        self,
        member:     OrganisationMember,
        new_status: OrgMemberStatus,
    ) -> OrganisationMember:
        member.status = new_status
        if new_status in (OrgMemberStatus.REMOVED, OrgMemberStatus.LEFT):
            member.removed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return member

    # ── OrganisationInvite lookups ────────────────────────────────────────────

    async def get_invite_by_id(
        self,
        invite_id: uuid.UUID,
    ) -> Optional[OrganisationInvite]:
        result = await self.db.execute(
            select(OrganisationInvite).where(OrganisationInvite.id == invite_id)
        )
        return result.scalar_one_or_none()

    async def get_invite_by_token_hash(
        self,
        token_hash: str,
    ) -> Optional[OrganisationInvite]:
        """Primary lookup for invite redemption via email link."""
        result = await self.db.execute(
            select(OrganisationInvite).where(
                OrganisationInvite.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_invite_by_email(
        self,
        org_id: uuid.UUID,
        email:  str,
    ) -> Optional[OrganisationInvite]:
        result = await self.db.execute(
            select(OrganisationInvite).where(
                and_(
                    OrganisationInvite.organisation_id == org_id,
                    OrganisationInvite.invited_email   == email,
                    OrganisationInvite.status          == OrgInviteStatus.PENDING,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_invite_for_user(
        self,
        org_id:  uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OrganisationInvite]:
        result = await self.db.execute(
            select(OrganisationInvite).where(
                and_(
                    OrganisationInvite.organisation_id  == org_id,
                    OrganisationInvite.invited_user_id  == user_id,
                    OrganisationInvite.status           == OrgInviteStatus.PENDING,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_invites_for_org(
        self,
        org_id: uuid.UUID,
    ) -> list[OrganisationInvite]:
        result = await self.db.execute(
            select(OrganisationInvite).where(
                and_(
                    OrganisationInvite.organisation_id == org_id,
                    OrganisationInvite.status          == OrgInviteStatus.PENDING,
                )
            ).order_by(OrganisationInvite.created_at.desc())
        )
        return list(result.scalars().all())

    # ── OrganisationInvite create / update ────────────────────────────────────

    async def create_invite(
        self,
        *,
        org_id:          uuid.UUID,
        invited_by_id:   uuid.UUID,
        invited_role:    OrgMemberRole,
        token_hash:      str,
        expires_at:      datetime,
        invited_email:   Optional[str]       = None,
        invited_user_id: Optional[uuid.UUID] = None,
        message:         Optional[str]       = None,
    ) -> OrganisationInvite:
        """
        INSERT an OrganisationInvite row (status=PENDING).
        At least one of invited_email or invited_user_id must be non-null
        (enforced in the service layer).
        """
        invite = OrganisationInvite(
            organisation_id=org_id,
            invited_by_id=invited_by_id,
            invited_role=invited_role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_email=invited_email,
            invited_user_id=invited_user_id,
            message=message,
            status=OrgInviteStatus.PENDING,
        )
        self.db.add(invite)
        await self.db.flush()
        await self.db.refresh(invite)
        log.debug(
            "org_invite.created",
            org_id=str(org_id),
            invited_email=invited_email,
            invited_user_id=str(invited_user_id) if invited_user_id else None,
        )
        return invite

    async def update_invite_status(
        self,
        invite:     OrganisationInvite,
        new_status: OrgInviteStatus,
    ) -> OrganisationInvite:
        invite.status       = new_status
        invite.responded_at = datetime.now(timezone.utc)
        await self.db.flush()
        return invite

    # ── Public org discovery ──────────────────────────────────────────────────

    async def list_public(
        self,
        *,
        search:        Optional[str]     = None,
        org_type:      Optional[OrgType] = None,
        verified_only: bool              = True,
        sort:          str               = "name",   # name | created
        page:          int               = 1,
        limit:         int               = 20,
    ) -> tuple[list[Organisation], int]:
        """
        Return (items, total_count) for the public org discovery page.
        Only ACTIVE orgs are ever returned; verified_only filters further.
        """
        base = (
            select(Organisation)
            .where(Organisation.status == OrgStatus.ACTIVE)
        )

        if verified_only:
            base = base.where(Organisation.is_verified == True)  # noqa: E712

        if org_type:
            base = base.where(Organisation.org_type == org_type)

        if search:
            term = f"%{search.strip().lower()}%"
            base = base.where(
                or_(
                    func.lower(Organisation.display_name).like(term),
                    func.lower(Organisation.legal_name).like(term),
                    func.lower(Organisation.slug).like(term),
                )
            )

        # total count (same filters, no pagination)
        count_q = select(func.count()).select_from(base.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        # sort
        if sort == "created":
            base = base.order_by(Organisation.created_at.desc())
        else:
            base = base.order_by(func.lower(Organisation.display_name).asc())

        # pagination
        offset = (page - 1) * limit
        base   = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).scalars().all()
        return list(rows), total

    async def expire_stale_invites(self) -> int:
        """
        Bulk-expire PENDING invites past their expires_at deadline.
        Called by a Celery beat task (not per-request).
        Returns the count of expired rows.
        """
        from sqlalchemy import func
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(OrganisationInvite)
            .where(
                and_(
                    OrganisationInvite.status     == OrgInviteStatus.PENDING,
                    OrganisationInvite.expires_at  < now,
                )
            )
            .values(status=OrgInviteStatus.EXPIRED, responded_at=now)
        )
        await self.db.flush()
        count = result.rowcount
        if count:
            log.info("org_invite.bulk_expired", count=count)
        return count
