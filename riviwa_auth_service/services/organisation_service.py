# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/organisation_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/organisation_service.py
═══════════════════════════════════════════════════════════════════════════════
Organisation lifecycle — creation, verification, membership, invites.

Each public method:
  1. Validates business rules
  2. Delegates DB writes to OrganisationRepository (flush only)
  3. Commits via the injected AsyncSession
  4. Publishes a Kafka event via EventPublisher

Kafka events published
──────────────────────
  organisation.created
  organisation.updated
  organisation.verified
  organisation.suspended  | banned | deactivated
  organisation.member_added
  organisation.member_removed
  organisation.member_role_changed
  organisation.owner_transferred
  organisation.invite_sent
  organisation.invite_accepted
  organisation.invite_declined
  organisation.invite_cancelled
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ForbiddenError,
    InviteAlreadyPendingError,
    InviteNotFoundError,
    OrgMemberAlreadyExistsError,
    OrgMemberNotFoundError,
    OrgMembershipRequiredError,
    OrgNotFoundError,
    OrgSlugAlreadyExistsError,
    ValidationError,
)
from core.security import generate_secure_token, hash_token
from events.publisher import EventPublisher
from events.topics import OrgEvents
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
from repositories.organisation_repository import OrganisationRepository
from repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)

# Invite link validity window
_INVITE_EXPIRE_DAYS = 7


class OrganisationService:

    def __init__(
        self,
        db:        AsyncSession,
        publisher: EventPublisher,
    ) -> None:
        self.db        = db
        self.publisher = publisher
        self.org_repo  = OrganisationRepository(db)
        self.user_repo = UserRepository(db)

    # ── Create organisation ───────────────────────────────────────────────────

    async def create(
        self,
        *,
        created_by_id:       uuid.UUID,
        legal_name:          str,
        display_name:        str,
        slug:                str,
        org_type:            OrgType,
        description:         Optional[str] = None,
        logo_url:            Optional[str] = None,
        website_url:         Optional[str] = None,
        support_email:       Optional[str] = None,
        support_phone:       Optional[str] = None,
        country_code:        Optional[str] = None,
        timezone:            Optional[str] = None,
        registration_number: Optional[str] = None,
        tax_id:              Optional[str] = None,
        max_members:         int           = 0,
    ) -> Organisation:
        """
        Create a new Organisation.

        Steps:
          1. Verify slug is unique.
          2. INSERT Organisation (status=PENDING_VERIFICATION).
          3. INSERT OrganisationMember for the creator with role=OWNER.
          4. Commit.
          5. Publish organisation.created + organisation.member_added.

        The org starts as PENDING_VERIFICATION — a platform admin must verify
        it (via verify()) before it can transact.
        """
        if await self.org_repo.slug_exists(slug):
            raise OrgSlugAlreadyExistsError()

        # INSERT org
        org = await self.org_repo.create(
            legal_name=legal_name,
            display_name=display_name,
            slug=slug,
            org_type=org_type,
            created_by_id=created_by_id,
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

        # INSERT creator as OWNER member
        membership = await self.org_repo.add_member(
            org_id=org.id,
            user_id=created_by_id,
            org_role=OrgMemberRole.OWNER,
            invited_by_id=None,       # creator was not invited
            status=OrgMemberStatus.ACTIVE,
        )

        await self.db.commit()

        log.info(
            "organisation.created",
            org_id=str(org.id),
            slug=slug,
            org_type=org_type.value,
            created_by_id=str(created_by_id),
        )

        # Publish events
        await self.publisher.organisation_created(org, created_by_id=created_by_id)
        await self.publisher.organisation_member_added(membership, invited_by_id=None)

        return org

    # ── Verify organisation (platform admin) ──────────────────────────────────

    async def verify(
        self,
        org_id:         uuid.UUID,
        verified_by_id: uuid.UUID,
    ) -> Organisation:
        """
        Platform admin approves the organisation.
        Transitions status: PENDING_VERIFICATION → ACTIVE, is_verified=True.
        Publishes organisation.verified.
        """
        org = await self._get_or_404(org_id)

        if org.status != OrgStatus.PENDING_VERIFICATION:
            raise ValidationError(
                f"Organisation status is '{org.status.value}'; cannot verify."
            )

        org = await self.org_repo.verify(org, verified_by_id)
        await self.db.commit()

        log.info("organisation.verified", org_id=str(org_id), verified_by=str(verified_by_id))
        await self.publisher.organisation_verified(org, verified_by_id=verified_by_id)
        return org

    # ── Update org profile ────────────────────────────────────────────────────

    async def update(
        self,
        org:     Organisation,
        updates: dict,
    ) -> Organisation:
        allowed = {
            "legal_name", "display_name", "slug", "description", "logo_url",
            "website_url", "support_email", "support_phone", "country_code",
            "timezone", "registration_number", "tax_id", "max_members",
        }
        changed_fields = [k for k in updates if k in allowed]
        if not changed_fields:
            return org

        # Check slug uniqueness if slug is being changed
        if "slug" in updates and updates["slug"] != org.slug:
            if await self.org_repo.slug_exists(updates["slug"]):
                raise OrgSlugAlreadyExistsError()

        org = await self.org_repo.update(org, **{k: updates[k] for k in changed_fields})
        await self.db.commit()

        log.info("organisation.updated", org_id=str(org.id), fields=changed_fields)
        await self.publisher.organisation_updated(org, changed_fields=changed_fields)
        return org

    # ── Status changes ────────────────────────────────────────────────────────

    async def suspend(
        self,
        org_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Organisation:
        org = await self._get_or_404(org_id)
        await self.org_repo.set_status(org_id, OrgStatus.SUSPENDED)
        await self.db.commit()
        org = await self.org_repo.get_by_id(org_id)
        await self.publisher.organisation_status_changed(
            org, OrgEvents.SUSPENDED, reason=reason
        )
        return org

    async def ban(
        self,
        org_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Organisation:
        org = await self._get_or_404(org_id)
        await self.org_repo.set_status(org_id, OrgStatus.BANNED)
        await self.db.commit()
        org = await self.org_repo.get_by_id(org_id)
        await self.publisher.organisation_status_changed(
            org, OrgEvents.BANNED, reason=reason
        )
        return org

    async def deactivate(
        self,
        org:    Organisation,
        reason: Optional[str] = None,
    ) -> None:
        """Owner-initiated closure."""
        await self.org_repo.soft_delete(org.id)
        await self.db.commit()
        org = await self.org_repo.get_by_id(org.id)
        await self.publisher.organisation_status_changed(
            org, OrgEvents.DEACTIVATED, reason=reason
        )

    # ── Member management ─────────────────────────────────────────────────────

    async def add_member_directly(
        self,
        org_id:       uuid.UUID,
        user_id:      uuid.UUID,
        org_role:     OrgMemberRole,
        added_by_id:  uuid.UUID,
    ) -> OrganisationMember:
        """
        Add an existing platform user directly (no invite token flow).
        Caller must hold at least ADMIN role (enforced in the endpoint).
        Raises OrgMemberAlreadyExistsError if the user is already a member.
        """
        existing = await self.org_repo.get_member(org_id, user_id)
        if existing and existing.status == OrgMemberStatus.ACTIVE:
            raise OrgMemberAlreadyExistsError()

        if org_role == OrgMemberRole.OWNER:
            raise ValidationError(
                "Cannot assign OWNER role directly. Use transfer_ownership instead."
            )

        membership = await self.org_repo.add_member(
            org_id=org_id,
            user_id=user_id,
            org_role=org_role,
            invited_by_id=added_by_id,
            status=OrgMemberStatus.ACTIVE,
        )
        await self.db.commit()

        log.info(
            "org_member.added_directly",
            org_id=str(org_id),
            user_id=str(user_id),
            role=org_role.value,
        )
        await self.publisher.organisation_member_added(
            membership, invited_by_id=added_by_id
        )
        return membership

    async def remove_member(
        self,
        org_id:         uuid.UUID,
        user_id:        uuid.UUID,
        removed_by_id:  uuid.UUID,
        reason:         Optional[str] = None,
    ) -> None:
        """
        Set membership status to REMOVED.
        Cannot remove the OWNER (they must transfer first).
        """
        member = await self.org_repo.get_active_member(org_id, user_id)
        if not member:
            raise OrgMemberNotFoundError()
        if member.org_role == OrgMemberRole.OWNER:
            raise ForbiddenError("Cannot remove the organisation owner. Transfer ownership first.")

        await self.org_repo.update_member_status(member, OrgMemberStatus.REMOVED)
        await self.db.commit()

        log.info("org_member.removed", org_id=str(org_id), user_id=str(user_id))
        await self.publisher.organisation_member_removed(
            org_id=org_id,
            user_id=user_id,
            removed_by_id=removed_by_id,
            reason=reason,
        )

    async def change_member_role(
        self,
        org_id:       uuid.UUID,
        user_id:      uuid.UUID,
        new_role:     OrgMemberRole,
        changed_by_id: uuid.UUID,
    ) -> OrganisationMember:
        if new_role == OrgMemberRole.OWNER:
            raise ValidationError("Use transfer_ownership to assign OWNER role.")

        member = await self.org_repo.get_active_member(org_id, user_id)
        if not member:
            raise OrgMemberNotFoundError()
        if member.org_role == OrgMemberRole.OWNER:
            raise ForbiddenError("Cannot change the role of the organisation owner.")

        old_role = member.org_role
        member = await self.org_repo.update_member_role(member, new_role)
        await self.db.commit()

        log.info(
            "org_member.role_changed",
            org_id=str(org_id),
            user_id=str(user_id),
            from_role=old_role.value,
            to_role=new_role.value,
        )
        # Publish member_role_changed event
        await self.publisher.organisation_member_role_changed(
            org_id=org_id,
            user_id=user_id,
            from_role=old_role.value,
            to_role=new_role.value,
            changed_by_id=changed_by_id,
        )
        return member

    async def transfer_ownership(
        self,
        org_id:          uuid.UUID,
        current_owner_id: uuid.UUID,
        new_owner_id:    uuid.UUID,
    ) -> None:
        """
        Transfer OWNER role from current_owner to new_owner.
        Both must be ACTIVE members of the org.
        """
        current = await self.org_repo.get_active_member(org_id, current_owner_id)
        if not current or current.org_role != OrgMemberRole.OWNER:
            raise ForbiddenError("Only the current owner can transfer ownership.")

        new_owner = await self.org_repo.get_active_member(org_id, new_owner_id)
        if not new_owner:
            raise OrgMemberNotFoundError("The new owner must already be an active member.")

        # Demote old owner → ADMIN, promote new owner → OWNER
        await self.org_repo.update_member_role(current, OrgMemberRole.ADMIN)
        await self.org_repo.update_member_role(new_owner, OrgMemberRole.OWNER)
        await self.db.commit()

        log.info(
            "org.ownership_transferred",
            org_id=str(org_id),
            from_user=str(current_owner_id),
            to_user=str(new_owner_id),
        )
        await self.publisher.organisation_ownership_transferred(
            org_id=org_id,
            previous_owner_id=current_owner_id,
            new_owner_id=new_owner_id,
        )

    # ── Invite flow ───────────────────────────────────────────────────────────

    async def send_invite(
        self,
        org_id:          uuid.UUID,
        invited_by_id:   uuid.UUID,
        invited_role:    OrgMemberRole,
        invited_email:   Optional[str]       = None,
        invited_user_id: Optional[uuid.UUID] = None,
        message:         Optional[str]       = None,
    ) -> OrganisationInvite:
        """
        Create a pending org invite.

        Rules:
          · invited_role cannot be OWNER.
          · At least one of invited_email / invited_user_id must be set.
          · No duplicate PENDING invite for the same (org, email) or (org, user_id).
        """
        if invited_role == OrgMemberRole.OWNER:
            raise ValidationError(
                "Cannot invite someone as OWNER. Use transfer_ownership instead."
            )
        if not invited_email and not invited_user_id:
            raise ValidationError("Either invited_email or invited_user_id must be provided.")

        # Duplicate check
        if invited_email:
            dup = await self.org_repo.get_pending_invite_by_email(org_id, invited_email)
            if dup:
                raise InviteAlreadyPendingError()
        if invited_user_id:
            dup = await self.org_repo.get_pending_invite_for_user(org_id, invited_user_id)
            if dup:
                raise InviteAlreadyPendingError()

        # Generate secure invite token
        raw_token  = generate_secure_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=_INVITE_EXPIRE_DAYS)

        invite = await self.org_repo.create_invite(
            org_id=org_id,
            invited_by_id=invited_by_id,
            invited_role=invited_role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_email=invited_email,
            invited_user_id=invited_user_id,
            message=message,
        )
        await self.db.commit()

        log.info(
            "org_invite.sent",
            org_id=str(org_id),
            invited_email=invited_email,
            invited_user_id=str(invited_user_id) if invited_user_id else None,
        )
        await self.publisher.organisation_invite_sent(
            org_id=org_id,
            invited_by_id=invited_by_id,
            invited_email=invited_email,
            invited_user_id=invited_user_id,
            invited_role=invited_role.value,
        )

        # TODO: dispatch email task with raw_token in the link
        # await send_invite_email.delay(
        #     email=invited_email, raw_token=raw_token, org_id=str(org_id)
        # )

        return invite

    async def accept_invite(
        self,
        token_hash: str,
        user_id:    uuid.UUID,
    ) -> OrganisationMember:
        """
        Accept an invite by redeeming the raw token (hashed before lookup).
        Creates the OrganisationMember row and marks the invite as ACCEPTED.
        """
        invite = await self.org_repo.get_invite_by_token_hash(token_hash)
        if not invite or not invite.is_valid():
            raise InviteNotFoundError()

        # Check user is not already a member
        existing = await self.org_repo.get_active_member(invite.organisation_id, user_id)
        if existing:
            raise OrgMemberAlreadyExistsError()

        now = datetime.now(timezone.utc)
        membership = await self.org_repo.add_member(
            org_id=invite.organisation_id,
            user_id=user_id,
            org_role=invite.invited_role,
            invited_by_id=invite.invited_by_id,
            status=OrgMemberStatus.ACTIVE,
        )
        await self.org_repo.update_invite_status(invite, OrgInviteStatus.ACCEPTED)
        await self.db.commit()

        log.info(
            "org_invite.accepted",
            org_id=str(invite.organisation_id),
            user_id=str(user_id),
        )
        await self.publisher.organisation_member_added(
            membership, invited_by_id=invite.invited_by_id
        )
        await self.publisher.organisation_invite_accepted(
            org_id=invite.organisation_id,
            user_id=user_id,
            invite_id=invite.id,
        )
        return membership

    async def decline_invite(
        self,
        token_hash: str,
        user_id:    uuid.UUID,
    ) -> None:
        invite = await self.org_repo.get_invite_by_token_hash(token_hash)
        if not invite or not invite.is_valid():
            raise InviteNotFoundError()

        await self.org_repo.update_invite_status(invite, OrgInviteStatus.DECLINED)
        await self.db.commit()

        log.info(
            "org_invite.declined",
            org_id=str(invite.organisation_id),
            user_id=str(user_id),
        )
        await self.publisher.organisation_invite_declined(
            org_id=invite.organisation_id,
            user_id=user_id,
            invite_id=invite.id,
        )

    async def cancel_invite(
        self,
        invite_id:      uuid.UUID,
        cancelled_by_id: uuid.UUID,
    ) -> None:
        invite = await self.org_repo.get_invite_by_id(invite_id)
        if not invite or invite.status != OrgInviteStatus.PENDING:
            raise InviteNotFoundError()

        await self.org_repo.update_invite_status(invite, OrgInviteStatus.CANCELLED)
        await self.db.commit()

        log.info(
            "org_invite.cancelled",
            invite_id=str(invite_id),
            cancelled_by=str(cancelled_by_id),
        )
        await self.publisher.organisation_invite_cancelled(
            org_id=invite.organisation_id,
            invite_id=invite_id,
            cancelled_by_id=cancelled_by_id,
        )

    # ── Dashboard switching ───────────────────────────────────────────────────

    async def switch_dashboard(
        self,
        user_id: uuid.UUID,
        org_id:  Optional[uuid.UUID],
    ) -> None:
        """
        Switch the user's active dashboard context.

        org_id=None  → personal/consumer view
        org_id=UUID  → org dashboard (validates active membership first)
        """
        if org_id is not None:
            member = await self.org_repo.get_active_member(org_id, user_id)
            if not member:
                raise OrgMembershipRequiredError()

        await user_repo.update_active_org(user_id, org_id)
        await self.db.commit()

        log.info(
            "auth.dashboard_switched",
            user_id=str(user_id),
            org_id=str(org_id) if org_id else "personal",
        )
        await self.publisher.auth_dashboard_switched(user_id, org_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    # ── Public org discovery ─────────────────────────────────────────────────

    async def list_public(
        self,
        *,
        search:        Optional[str]     = None,
        org_type:      Optional[OrgType] = None,
        verified_only: bool              = True,
        sort:          str               = "name",
        page:          int               = 1,
        limit:         int               = 20,
    ) -> tuple[list[Organisation], int]:
        """
        Return paginated list of public-visible orgs.
        Only ACTIVE (+ optionally verified) orgs are exposed.
        No auth required — open discovery endpoint.
        """
        return await self.repo.list_public(
            search=search,
            org_type=org_type,
            verified_only=verified_only,
            sort=sort,
            page=page,
            limit=limit,
        )

    async def _get_or_404(self, org_id: uuid.UUID) -> Organisation:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise OrgNotFoundError()
        return org
