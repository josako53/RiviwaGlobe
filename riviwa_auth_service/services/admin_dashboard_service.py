# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/admin_dashboard_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/admin_dashboard_service.py
════════════════════════════════════════════════════════════════════════════
Business logic layer for the platform admin dashboard.

Responsibilities:
  · Validate admin permissions before executing actions
  · Delegate DB reads to AdminDashboardRepository
  · Delegate DB writes to UserRepository / OrganisationRepository
  · Publish Kafka events after every write operation (audit trail)
  · Convert raw repository dicts/ORM objects → typed Pydantic response schemas
  · Return typed response objects ready for FastAPI to serialise

This layer keeps all transformation logic out of the API handlers and all
raw SQL out of the API handlers.

What this service does NOT do:
  · It does not make HTTP calls to feedback_service or payment_service.
    Cross-service data (GRM counts, payment totals) is aggregated by the
    frontend or a BFF layer that calls each service independently.
  · It does not cache results — caching (Redis) belongs in a future layer.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ForbiddenError, NotFoundError
from events.publisher import EventPublisher
from events.topics import UserEvents, OrgEvents
from models.organisation import OrgStatus
from models.user import AccountStatus
from repositories.admin_dashboard_repository import AdminDashboardRepository
from repositories.organisation_repository import OrganisationRepository
from repositories.user_repository import UserRepository
from schemas.admin_dashboard import (
    AdminOrgDetail,
    AdminOrgListItem,
    AdminOrgListResponse,
    AdminProjectListItem,
    AdminProjectListResponse,
    AdminProjectSummaryResponse,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
    ChecklistHealthResponse,
    FlaggedUserItem,
    FlaggedUserListResponse,
    FraudSummaryResponse,
    ModerationActionResponse,
    OrgBreakdownRow,
    OrgGrowthRow,
    OrgMemberDistributionRow,
    PendingOrgItem,
    PendingVerificationQueueResponse,
    PlatformStaffItem,
    PlatformSummaryResponse,
    RecentAdminActionItem,
    RoleAssignmentResponse,
    UserGrowthRow,
    UserStatusBreakdownRow,
)

log = structlog.get_logger(__name__)


class AdminDashboardService:
    """
    Service layer for platform admin dashboard operations.

    Instantiate once per request:
        svc = AdminDashboardService(db=db, publisher=publisher)

    All write methods commit the DB transaction and publish a Kafka event.
    All read methods are read-only and never commit.
    """

    def __init__(
        self,
        db:        AsyncSession,
        publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.db        = db
        self.publisher = publisher
        self._repo     = AdminDashboardRepository(db)
        self._users    = UserRepository(db)
        self._orgs     = OrganisationRepository(db)

    # ── 1. Platform summary ───────────────────────────────────────────────────

    async def get_platform_summary(self) -> PlatformSummaryResponse:
        """
        Return the complete platform KPI summary for the admin home page.
        Single DB round-trip set — optimised for the landing card view.
        """
        raw = await self._repo.platform_summary()
        resp = PlatformSummaryResponse.from_dict(raw)
        log.debug("admin.dashboard.summary_fetched")
        return resp

    # ── 2. Users ──────────────────────────────────────────────────────────────

    async def list_users(
        self,
        status:        Optional[str]  = None,
        search:        Optional[str]  = None,
        platform_role: Optional[str]  = None,
        from_date:     Optional[date] = None,
        to_date:       Optional[date] = None,
        skip:          int = 0,
        limit:         int = 50,
    ) -> AdminUserListResponse:
        """Paginated user list with optional filters."""
        users, total = await self._repo.list_users(
            status=status, search=search, platform_role=platform_role,
            from_date=from_date, to_date=to_date, skip=skip, limit=limit,
        )
        items = [
            AdminUserListItem(
                id            = u.id,
                display_name  = u.display_name,
                email         = u.email,
                phone         = u.phone_number,
                username      = u.username,
                status        = u.status,
                created_at    = u.created_at.isoformat() if u.created_at else None,
                last_login_at = u.last_login_at.isoformat() if u.last_login_at else None,
                fraud_score   = u.fraud_score,
            )
            for u in users
        ]
        return AdminUserListResponse(
            total=total, returned=len(items), skip=skip, limit=limit, items=items
        )

    async def get_user_detail(self, user_id: uuid.UUID) -> AdminUserDetail:
        """Full user detail for the admin user management screen."""
        user = await self._users.get_by_id_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        return AdminUserDetail(
            id                    = user.id,
            display_name          = user.display_name,
            email                 = user.email,
            phone                 = user.phone_number,
            username              = user.username,
            status                = user.status,
            email_verified        = bool(user.is_email_verified),
            phone_verified        = bool(user.phone_verified),
            fraud_score           = user.fraud_score,
            language              = user.language,
            created_at            = user.created_at.isoformat() if user.created_at else None,
            last_login_at         = user.last_login_at.isoformat() if user.last_login_at else None,
            failed_login_attempts = user.failed_login_attempts or 0,
            platform_roles        = [
                ur.role.name for ur in (user.platform_roles or []) if ur.role
            ],
        )

    async def get_user_growth_trend(self, days: int = 30) -> List[UserGrowthRow]:
        rows = await self._repo.user_growth_trend(days=days)
        return [UserGrowthRow(**r) for r in rows]

    async def get_user_status_breakdown(self) -> List[UserStatusBreakdownRow]:
        rows = await self._repo.user_status_breakdown()
        return [UserStatusBreakdownRow(**r) for r in rows]

    async def suspend_user(
        self,
        user_id:      uuid.UUID,
        reason:       Optional[str],
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        """
        Suspend a user account.
        Publishes user.suspended Kafka event for notification_service.
        """
        user = await self._users.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if user.status == AccountStatus.SUSPENDED:
            raise ForbiddenError("User is already suspended.")
        if user.status == AccountStatus.BANNED:
            raise ForbiddenError("Cannot suspend a banned account.")

        await self._users.set_status(user_id, AccountStatus.SUSPENDED)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.user.suspended",
                 user_id=str(user_id), by=str(admin_user_id), reason=reason)

        if self.publisher:
            await self.publisher.user_status_changed(
                user, UserEvents.SUSPENDED, reason or "Platform moderation"
            )
            # Notify the user
            await self.publisher.notifications.account_status_changed(
                recipient_user_id = str(user_id),
                notification_type = "system.account_suspended",
                reason            = reason,
                language          = user.language or "en",
            )

        return ModerationActionResponse(
            message     = "User suspended.",
            entity_type = "user",
            entity_id   = user_id,
            new_status  = "suspended",
            action_at   = now.isoformat(),
        )

    async def ban_user(
        self,
        user_id:       uuid.UUID,
        reason:        str,
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        """
        Permanently ban a user. Publishes user.banned event.
        """
        user = await self._users.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if user.status == AccountStatus.BANNED:
            raise ForbiddenError("User is already banned.")

        await self._users.set_status(user_id, AccountStatus.BANNED)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.user.banned",
                 user_id=str(user_id), by=str(admin_user_id), reason=reason)

        if self.publisher:
            await self.publisher.user_status_changed(user, UserEvents.BANNED, reason)
            await self.publisher.notifications.account_status_changed(
                recipient_user_id = str(user_id),
                notification_type = "system.account_banned",
                reason            = reason,
                language          = user.language or "en",
            )

        return ModerationActionResponse(
            message     = "User permanently banned.",
            entity_type = "user",
            entity_id   = user_id,
            new_status  = "banned",
            action_at   = now.isoformat(),
        )

    async def reactivate_user(
        self,
        user_id:       uuid.UUID,
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        """Restore a suspended or deactivated user to ACTIVE."""
        user = await self._users.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if user.status == AccountStatus.ACTIVE:
            raise ForbiddenError("User is already active.")
        if user.status == AccountStatus.BANNED:
            raise ForbiddenError(
                "Cannot reactivate a banned account. Use a different process."
            )

        await self._users.set_status(user_id, AccountStatus.ACTIVE)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.user.reactivated",
                 user_id=str(user_id), by=str(admin_user_id))

        if self.publisher:
            await self.publisher.user_status_changed(
                user, UserEvents.REACTIVATED, "Reactivated by platform admin"
            )
            await self.publisher.notifications.account_status_changed(
                recipient_user_id = str(user_id),
                notification_type = "system.account_reactivated",
                language          = user.language or "en",
            )

        return ModerationActionResponse(
            message     = "User reactivated.",
            entity_type = "user",
            entity_id   = user_id,
            new_status  = "active",
            action_at   = now.isoformat(),
        )

    # ── 3. Organisations ──────────────────────────────────────────────────────

    async def list_organisations(
        self,
        status:    Optional[str]  = None,
        org_type:  Optional[str]  = None,
        search:    Optional[str]  = None,
        from_date: Optional[date] = None,
        to_date:   Optional[date] = None,
        skip:      int = 0,
        limit:     int = 50,
    ) -> AdminOrgListResponse:
        orgs, total = await self._repo.list_organisations(
            status=status, org_type=org_type, search=search,
            from_date=from_date, to_date=to_date, skip=skip, limit=limit,
        )
        items = [
            AdminOrgListItem(
                id          = o.id,
                name        = o.display_name,
                slug        = o.slug,
                org_type    = o.org_type,
                status      = o.status,
                is_verified = bool(o.is_verified),
                created_at  = o.created_at.isoformat() if o.created_at else None,
            )
            for o in orgs
        ]
        return AdminOrgListResponse(
            total=total, returned=len(items), skip=skip, limit=limit, items=items
        )

    async def get_pending_verification_queue(self) -> PendingVerificationQueueResponse:
        """Return all orgs awaiting verification, oldest first."""
        orgs = await self._repo.pending_verification_queue()
        items = [
            PendingOrgItem(
                id         = o.id,
                name       = o.display_name,
                slug       = o.slug,
                org_type   = o.org_type,
                created_at = o.created_at.isoformat() if o.created_at else None,
            )
            for o in orgs
        ]
        return PendingVerificationQueueResponse(count=len(items), items=items)

    async def get_org_breakdown(self) -> List[OrgBreakdownRow]:
        rows = await self._repo.org_breakdown_by_type()
        return [OrgBreakdownRow(**r) for r in rows]

    async def get_org_growth_trend(self, days: int = 30) -> List[OrgGrowthRow]:
        rows = await self._repo.org_growth_trend(days=days)
        return [OrgGrowthRow(**r) for r in rows]

    async def get_org_member_distribution(self) -> List[OrgMemberDistributionRow]:
        rows = await self._repo.org_member_distribution()
        return [OrgMemberDistributionRow(**r) for r in rows]

    async def get_org_detail(self, org_id: uuid.UUID) -> AdminOrgDetail:
        org = await self._orgs.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organisation {org_id} not found.")
        member_count = await self._orgs.count_active_members(org_id)
        return AdminOrgDetail(
            id            = org.id,
            name          = org.display_name,
            slug          = org.slug,
            org_type      = org.org_type,
            status        = org.status,
            is_verified   = bool(org.is_verified),
            country       = org.country_code,
            contact_email = org.support_email,
            contact_phone = org.support_phone,
            created_at    = org.created_at.isoformat() if org.created_at else None,
            member_count  = member_count,
        )

    async def verify_organisation(
        self,
        org_id:        uuid.UUID,
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        """Approve an organisation's verification request."""
        org = await self._orgs.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organisation {org_id} not found.")

        await self._orgs.verify(org, admin_user_id)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.org.verified", org_id=str(org_id), by=str(admin_user_id))

        if self.publisher:
            await self.publisher.org_verified(org)

        return ModerationActionResponse(
            message     = "Organisation verified.",
            entity_type = "organisation",
            entity_id   = org_id,
            new_status  = "active",
            action_at   = now.isoformat(),
        )

    async def suspend_organisation(
        self,
        org_id:        uuid.UUID,
        reason:        Optional[str],
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        org = await self._orgs.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organisation {org_id} not found.")
        if org.status == OrgStatus.SUSPENDED:
            raise ForbiddenError("Organisation is already suspended.")

        await self._orgs.set_status(org_id, OrgStatus.SUSPENDED)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.org.suspended",
                 org_id=str(org_id), by=str(admin_user_id), reason=reason)

        if self.publisher:
            await self.publisher.org_status_changed(
                org, OrgEvents.SUSPENDED, reason or "Platform moderation"
            )

        return ModerationActionResponse(
            message     = "Organisation suspended.",
            entity_type = "organisation",
            entity_id   = org_id,
            new_status  = "suspended",
            action_at   = now.isoformat(),
        )

    async def ban_organisation(
        self,
        org_id:        uuid.UUID,
        reason:        str,
        admin_user_id: uuid.UUID,
    ) -> ModerationActionResponse:
        org = await self._orgs.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organisation {org_id} not found.")
        if org.status == OrgStatus.BANNED:
            raise ForbiddenError("Organisation is already banned.")

        await self._orgs.set_status(org_id, OrgStatus.BANNED)
        await self.db.commit()

        now = datetime.now(timezone.utc)
        log.info("admin.org.banned",
                 org_id=str(org_id), by=str(admin_user_id), reason=reason)

        if self.publisher:
            await self.publisher.org_status_changed(org, OrgEvents.BANNED, reason)

        return ModerationActionResponse(
            message     = "Organisation permanently banned.",
            entity_type = "organisation",
            entity_id   = org_id,
            new_status  = "banned",
            action_at   = now.isoformat(),
        )

    # ── 4. Projects ───────────────────────────────────────────────────────────

    async def list_projects(
        self,
        status:   Optional[str]       = None,
        org_id:   Optional[uuid.UUID] = None,
        sector:   Optional[str]       = None,
        region:   Optional[str]       = None,
        skip:     int = 0,
        limit:    int = 50,
    ) -> AdminProjectListResponse:
        projects, total = await self._repo.project_list(
            status=status, org_id=org_id, sector=sector,
            region=region, skip=skip, limit=limit,
        )
        items = [
            AdminProjectListItem(
                id           = p.id,
                name         = p.name,
                code         = p.project_code,
                org_id       = p.org_id,
                status       = p.status,
                sector       = p.sector,
                region       = p.region,
                lga          = p.lga,
                total_budget = p.budget_amount,
                start_date   = p.start_date.isoformat() if p.start_date else None,
                end_date     = p.end_date.isoformat() if p.end_date else None,
            )
            for p in projects
        ]
        return AdminProjectListResponse(
            total=total, returned=len(items), skip=skip, limit=limit, items=items
        )

    async def get_project_summary(self) -> AdminProjectSummaryResponse:
        raw = await self._repo.project_summary()
        return AdminProjectSummaryResponse(**raw)

    # ── 5. Security / fraud ───────────────────────────────────────────────────

    async def get_fraud_summary(self) -> FraudSummaryResponse:
        raw = await self._repo.fraud_flags_summary()
        return FraudSummaryResponse.from_dict(raw)

    async def list_flagged_users(
        self,
        action: Optional[str] = None,
        skip:       int = 0,
        limit:      int = 50,
    ) -> FlaggedUserListResponse:
        pairs, total = await self._repo.list_flagged_users(
            action=action, skip=skip, limit=limit,
        )
        items = [
            FlaggedUserItem(
                user_id      = u.id,
                display_name = u.display_name,
                email        = u.email,
                phone        = u.phone_number,
                user_status  = u.status,
                fraud_score  = f.total_score,
                risk_level   = f.action.value if hasattr(f.action, 'value') else f.action,
                assessed_at  = f.created_at.isoformat() if f.created_at else None,
            )
            for u, f in pairs
        ]
        return FlaggedUserListResponse(
            total=total, returned=len(items), skip=skip, limit=limit, items=items
        )

    # ── 6. Platform staff ─────────────────────────────────────────────────────

    async def list_platform_staff(self) -> List[PlatformStaffItem]:
        rows = await self._repo.list_platform_staff()
        return [
            PlatformStaffItem(
                user_id       = uuid.UUID(r["user_id"]),
                display_name  = r.get("display_name"),
                email         = r.get("email"),
                phone         = r.get("phone"),
                platform_role = r["platform_role"],
                status        = r["status"],
            )
            for r in rows
        ]

    async def assign_platform_role(
        self,
        user_id:       uuid.UUID,
        role_name:     str,
        by_user_id:    uuid.UUID,
    ) -> RoleAssignmentResponse:
        """
        Assign a platform role to a user.
        Only super_admin may call this — enforced at the API layer.
        """
        result = await self._repo.assign_platform_role(user_id, role_name)
        await self.db.commit()
        log.info("admin.role.assigned",
                 user_id=str(user_id), role=role_name, by=str(by_user_id))
        return RoleAssignmentResponse(
            message = f"Role '{role_name}' assigned.",
            user_id = user_id,
            role    = role_name,
        )

    async def revoke_platform_role(
        self,
        user_id:    uuid.UUID,
        role_name:  str,
        by_user_id: uuid.UUID,
    ) -> RoleAssignmentResponse:
        """Revoke a platform role. Only super_admin may call this."""
        revoked = await self._repo.revoke_platform_role(user_id, role_name)
        if not revoked:
            raise NotFoundError(f"Role '{role_name}' is not assigned to this user.")
        await self.db.commit()
        log.info("admin.role.revoked",
                 user_id=str(user_id), role=role_name, by=str(by_user_id))
        return RoleAssignmentResponse(
            message = f"Role '{role_name}' revoked.",
            user_id = user_id,
            role    = role_name,
        )

    # ── 7. Checklist health ───────────────────────────────────────────────────

    async def get_checklist_health(self) -> ChecklistHealthResponse:
        raw = await self._repo.checklist_health()
        return ChecklistHealthResponse(**raw)

    # ── 8. Recent admin actions ───────────────────────────────────────────────

    async def get_recent_admin_actions(
        self, limit: int = 50
    ) -> List[RecentAdminActionItem]:
        rows = await self._repo.recent_admin_actions(limit=limit)
        return [
            RecentAdminActionItem(
                entity_type = r["entity_type"],
                entity_id   = uuid.UUID(r["entity_id"]),
                name        = r.get("name"),
                action      = r["action"],
                at          = r.get("at"),
            )
            for r in rows
        ]
