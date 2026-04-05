# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/admin_dashboard_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/admin_dashboard_repository.py
════════════════════════════════════════════════════════════════════════════
All raw DB queries that back the platform admin dashboard.

This repository aggregates across:
  · users          — registration counts, status breakdown, growth trend
  · organisations  — total, by type, by status, pending verification queue
  · organisation_members — membership counts, roles distribution
  · org_projects   — projects by status, sector, region
  · fraud_assessments — flagged accounts, high-risk registrations
  · project_checklist_items — completion and overdue counts

NOTE: Payment and feedback stats are in their own services (feedback_service
port 8090, payment service port 8040). The dashboard endpoint in this service
covers auth_db data only. A BFF (Backend-For-Frontend) or the frontend itself
calls all three services and merges the results.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, case, cast, func, select
from sqlalchemy.types import Date
from sqlalchemy.ext.asyncio import AsyncSession

from models.fraud import FraudAssessment
from models.org_project import (
    OrgProject, OrgProjectStage, ProjectChecklistItem,
)
from models.organisation import Organisation, OrganisationMember, OrgMemberRole, OrgStatus, OrgType
from models.user import AccountStatus, User


class AdminDashboardRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Platform overview (single-call summary) ───────────────────────────────

    async def platform_summary(self) -> dict:
        """
        Returns the top-level platform KPIs in a single aggregated query set.
        Used by GET /admin/dashboard/summary.
        """
        now   = datetime.now(timezone.utc)
        today = date.today()
        month_start = today.replace(day=1)

        # ── Users ─────────────────────────────────────────────────────────────
        user_totals = await self.db.execute(
            select(
                User.status,
                func.count(User.id).label("cnt"),
            ).group_by(User.status)
        )
        user_by_status: dict[str, int] = {
            row.status: row.cnt for row in user_totals.all()
        }
        total_users   = sum(user_by_status.values())
        active_users  = user_by_status.get("active", 0)
        pending_users = sum(
            user_by_status.get(s, 0)
            for s in ("pending_email", "pending_phone", "pending_id", "channel_registered")
        )
        suspended_users = user_by_status.get("suspended", 0)
        banned_users    = user_by_status.get("banned", 0)

        # New users this month
        new_this_month = await self.db.scalar(
            select(func.count(User.id)).where(
                cast(User.created_at, Date) >= month_start
            )
        ) or 0

        # New users today
        new_today = await self.db.scalar(
            select(func.count(User.id)).where(
                cast(User.created_at, Date) == today
            )
        ) or 0

        # ── Organisations ─────────────────────────────────────────────────────
        org_totals = await self.db.execute(
            select(
                Organisation.status,
                func.count(Organisation.id).label("cnt"),
            ).group_by(Organisation.status)
        )
        org_by_status: dict[str, int] = {
            row.status: row.cnt for row in org_totals.all()
        }
        total_orgs         = sum(org_by_status.values())
        active_orgs        = org_by_status.get("active", 0)
        pending_verify     = org_by_status.get("pending_verification", 0)
        suspended_orgs     = org_by_status.get("suspended", 0)
        banned_orgs        = org_by_status.get("banned", 0)
        deactivated_orgs   = org_by_status.get("deactivated", 0)

        # ── Projects ──────────────────────────────────────────────────────────
        project_totals = await self.db.execute(
            select(
                OrgProject.status,
                func.count(OrgProject.id).label("cnt"),
            ).group_by(OrgProject.status)
        )
        project_by_status: dict[str, int] = {
            row.status: row.cnt for row in project_totals.all()
        }
        total_projects  = sum(project_by_status.values())
        active_projects = project_by_status.get("active", 0)

        # ── Fraud / security ──────────────────────────────────────────────────
        high_risk_count = await self.db.scalar(
            select(func.count(FraudAssessment.id)).where(
                FraudAssessment.action.in_(["review", "block"])
            )
        ) or 0

        return {
            "generated_at": now.isoformat(),
            "users": {
                "total":             total_users,
                "active":            active_users,
                "pending":           pending_users,
                "suspended":         suspended_users,
                "banned":            banned_users,
                "new_this_month":    new_this_month,
                "new_today":         new_today,
            },
            "organisations": {
                "total":             total_orgs,
                "active":            active_orgs,
                "pending_verification": pending_verify,
                "suspended":         suspended_orgs,
                "banned":            banned_orgs,
                "deactivated":       deactivated_orgs,
            },
            "projects": {
                "total":             total_projects,
                "active":            active_projects,
                "by_status":         project_by_status,
            },
            "security": {
                "high_risk_fraud_flags": high_risk_count,
            },
        }

    # ── User management ───────────────────────────────────────────────────────

    async def list_users(
        self,
        status:        Optional[str]  = None,
        search:        Optional[str]  = None,
        platform_role: Optional[str]  = None,
        from_date:     Optional[date] = None,
        to_date:       Optional[date] = None,
        skip:          int = 0,
        limit:         int = 50,
    ) -> tuple[list[User], int]:
        """
        Paginated user list with optional filters.
        Returns (users, total_count).
        """
        from models.user_role import UserRole
        from models.role import Role
        from sqlalchemy.orm import selectinload

        q = select(User).options(selectinload(User.platform_roles))

        if status:
            q = q.where(User.status == AccountStatus(status))
        if search:
            pattern = f"%{search}%"
            q = q.where(
                User.display_name.ilike(pattern)
                | User.email.ilike(pattern)
                | User.phone_number.ilike(pattern)
                | User.username.ilike(pattern)
            )
        if platform_role:
            q = (
                q.join(UserRole, UserRole.user_id == User.id)
                 .join(Role, Role.id == UserRole.role_id)
                 .where(Role.name == platform_role)
            )
        if from_date:
            q = q.where(cast(User.created_at, Date) >= from_date)
        if to_date:
            q = q.where(cast(User.created_at, Date) <= to_date)

        count_q = select(func.count()).select_from(q.subquery())
        total   = await self.db.scalar(count_q) or 0

        q = q.order_by(User.created_at.desc()).offset(skip).limit(limit)
        users = list((await self.db.execute(q)).scalars().unique().all())
        return users, total

    async def user_growth_trend(self, days: int = 30) -> list[dict]:
        """Daily new user registration count over the last N days."""
        since = date.today() - timedelta(days=days)
        rows = await self.db.execute(
            select(
                cast(User.created_at, Date).label("day"),
                func.count(User.id).label("registrations"),
                func.count(User.id).filter(
                    User.status == AccountStatus.ACTIVE
                ).label("active"),
            )
            .where(cast(User.created_at, Date) >= since)
            .group_by("day")
            .order_by("day")
        )
        return [
            {"date": str(r.day), "registrations": r.registrations, "active": r.active}
            for r in rows.all()
        ]

    async def user_status_breakdown(self) -> list[dict]:
        """Count of users per AccountStatus."""
        rows = await self.db.execute(
            select(User.status, func.count(User.id).label("count"))
            .group_by(User.status)
            .order_by(func.count(User.id).desc())
        )
        return [{"status": r.status, "count": r.count} for r in rows.all()]

    # ── Organisation management ───────────────────────────────────────────────

    async def list_organisations(
        self,
        status:    Optional[str] = None,
        org_type:  Optional[str] = None,
        search:    Optional[str] = None,
        from_date: Optional[date] = None,
        to_date:   Optional[date] = None,
        skip:      int = 0,
        limit:     int = 50,
    ) -> tuple[list[Organisation], int]:
        """Paginated organisation list for the admin management view."""
        q = select(Organisation)

        if status:
            q = q.where(Organisation.status == OrgStatus(status))
        if org_type:
            q = q.where(Organisation.org_type == OrgType(org_type))
        if search:
            pattern = f"%{search}%"
            q = q.where(
                Organisation.name.ilike(pattern)
                | Organisation.slug.ilike(pattern)
            )
        if from_date:
            q = q.where(cast(Organisation.created_at, Date) >= from_date)
        if to_date:
            q = q.where(cast(Organisation.created_at, Date) <= to_date)

        total = await self.db.scalar(
            select(func.count()).select_from(q.subquery())
        ) or 0
        q     = q.order_by(Organisation.created_at.desc()).offset(skip).limit(limit)
        orgs  = list((await self.db.execute(q)).scalars().all())
        return orgs, total

    async def pending_verification_queue(self) -> list[Organisation]:
        """All orgs awaiting platform admin verification, oldest first."""
        q = (
            select(Organisation)
            .where(Organisation.status == OrgStatus.PENDING_VERIFICATION)
            .order_by(Organisation.created_at.asc())
        )
        return list((await self.db.execute(q)).scalars().all())

    async def org_breakdown_by_type(self) -> list[dict]:
        rows = await self.db.execute(
            select(
                Organisation.org_type,
                Organisation.status,
                func.count(Organisation.id).label("count"),
            )
            .group_by(Organisation.org_type, Organisation.status)
            .order_by(Organisation.org_type)
        )
        return [
            {"org_type": r.org_type, "status": r.status, "count": r.count}
            for r in rows.all()
        ]

    async def org_growth_trend(self, days: int = 30) -> list[dict]:
        since = date.today() - timedelta(days=days)
        rows = await self.db.execute(
            select(
                cast(Organisation.created_at, Date).label("day"),
                func.count(Organisation.id).label("created"),
            )
            .where(cast(Organisation.created_at, Date) >= since)
            .group_by("day")
            .order_by("day")
        )
        return [{"date": str(r.day), "created": r.created} for r in rows.all()]

    async def org_member_distribution(self) -> list[dict]:
        """Average and total members per org across the platform."""
        rows = await self.db.execute(
            select(
                OrganisationMember.org_role,
                func.count(OrganisationMember.id).label("count"),
            )
            .where(OrganisationMember.status == "active")
            .group_by(OrganisationMember.org_role)
        )
        return [{"role": r.org_role, "count": r.count} for r in rows.all()]

    # ── Projects ──────────────────────────────────────────────────────────────

    async def project_summary(self) -> dict:
        """Cross-platform project statistics."""
        rows = await self.db.execute(
            select(
                OrgProject.status,
                OrgProject.sector,
                func.count(OrgProject.id).label("count"),
                func.sum(OrgProject.budget_amount).label("total_budget"),
            )
            .group_by(OrgProject.status, OrgProject.sector)
        )
        by_status: dict[str, int] = {}
        by_sector: dict[str, int] = {}
        total_budget = 0.0

        for r in rows.all():
            by_status[r.status] = by_status.get(r.status, 0) + r.count
            if r.sector:
                by_sector[r.sector] = by_sector.get(r.sector, 0) + r.count
            if r.total_budget:
                total_budget += float(r.total_budget)

        return {
            "by_status": by_status,
            "by_sector": by_sector,
            "total_budget_sum": round(total_budget, 2),
        }

    async def project_list(
        self,
        status:   Optional[str] = None,
        org_id:   Optional[uuid.UUID] = None,
        sector:   Optional[str] = None,
        region:   Optional[str] = None,
        skip:     int = 0,
        limit:    int = 50,
    ) -> tuple[list[OrgProject], int]:
        q = select(OrgProject)
        if status:
            q = q.where(OrgProject.status == status)
        if org_id:
            q = q.where(OrgProject.org_id == org_id)
        if sector:
            q = q.where(OrgProject.sector == sector)
        if region:
            q = q.where(OrgProject.region.ilike(f"%{region}%"))

        total = await self.db.scalar(
            select(func.count()).select_from(q.subquery())
        ) or 0
        q = q.order_by(OrgProject.created_at.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    # ── Security / Fraud ──────────────────────────────────────────────────────

    async def fraud_flags_summary(self) -> dict:
        """Platform-wide fraud assessment overview."""
        rows = await self.db.execute(
            select(
                FraudAssessment.action,
                func.count(FraudAssessment.id).label("count"),
                func.avg(FraudAssessment.total_score).label("avg_score"),
            )
            .group_by(FraudAssessment.action)
        )
        breakdown = {}
        for r in rows.all():
            breakdown[r.action if isinstance(r.action, str) else r.action.value] = {
                "count":     r.count,
                "avg_score": round(float(r.avg_score), 2) if r.avg_score else 0.0,
            }

        flagged_users = await self.db.scalar(
            select(func.count(User.id)).where(
                User.status == AccountStatus.PENDING_ID
            )
        ) or 0

        return {
            "by_action":              breakdown,
            "accounts_pending_id_verification": flagged_users,
        }

    async def list_flagged_users(
        self,
        action: Optional[str] = None,
        skip:       int = 0,
        limit:      int = 50,
    ) -> tuple[list, int]:
        """
        Users with review/block fraud assessment, joined with their
        most recent FraudAssessment record.
        """
        q = (
            select(User, FraudAssessment)
            .join(FraudAssessment, FraudAssessment.user_id == User.id)
            .order_by(FraudAssessment.total_score.desc())
        )
        if action:
            q = q.where(FraudAssessment.action == action)

        total = await self.db.scalar(
            select(func.count()).select_from(q.subquery())
        ) or 0
        rows = (await self.db.execute(q.offset(skip).limit(limit))).all()
        return [(r.User, r.FraudAssessment) for r in rows], total

    # ── Platform roles ────────────────────────────────────────────────────────

    async def list_platform_staff(self) -> list[dict]:
        """
        All users who have been assigned a platform role
        (moderator, admin, or super_admin).
        """
        from models.user_role import UserRole
        from models.role import Role

        rows = await self.db.execute(
            select(User, Role.name.label("role_name"))
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .order_by(Role.name, User.display_name)
        )
        return [
            {
                "user_id":      str(r.User.id),
                "display_name": r.User.display_name,
                "email":        r.User.email,
                "phone":        r.User.phone_number,
                "platform_role": r.role_name,
                "status":       r.User.status,
            }
            for r in rows.all()
        ]

    async def assign_platform_role(
        self,
        user_id:   uuid.UUID,
        role_name: str,
    ) -> dict:
        """
        Assign a platform role (moderator | admin | super_admin) to a user.
        Creates a UserRole row. Idempotent — no error if already assigned.
        """
        from models.user_role import UserRole
        from models.role import Role

        # Get role
        role = (await self.db.execute(
            select(Role).where(Role.name == role_name)
        )).scalar_one_or_none()
        if not role:
            raise ValueError(f"Role '{role_name}' not found.")

        # Check if already assigned
        existing = (await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role.id,
            )
        )).scalar_one_or_none()

        if not existing:
            ur = UserRole(user_id=user_id, role_id=role.id)
            self.db.add(ur)

        return {"user_id": str(user_id), "role": role_name}

    async def revoke_platform_role(
        self,
        user_id:   uuid.UUID,
        role_name: str,
    ) -> bool:
        from models.user_role import UserRole
        from models.role import Role

        role = (await self.db.execute(
            select(Role).where(Role.name == role_name)
        )).scalar_one_or_none()
        if not role:
            return False

        ur = (await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role.id,
            )
        )).scalar_one_or_none()
        if not ur:
            return False
        await self.db.delete(ur)
        return True

    # ── Platform-wide checklist health ───────────────────────────────────────

    async def checklist_health(self) -> dict:
        """
        Platform-wide checklist completion health.
        Aggregates across all active projects.
        """
        today = date.today()
        rows  = await self.db.execute(
            select(
                ProjectChecklistItem.status,
                func.count(ProjectChecklistItem.id).label("count"),
            )
            .where(ProjectChecklistItem.deleted_at.is_(None))
            .group_by(ProjectChecklistItem.status)
        )
        by_status = {r.status: r.count for r in rows.all()}
        total     = sum(by_status.values())
        done      = by_status.get("done", 0)
        skipped   = by_status.get("skipped", 0)
        blocked   = by_status.get("blocked", 0)
        denom     = total - skipped - blocked
        pct       = round(done / denom * 100, 1) if denom > 0 else 0.0

        overdue = await self.db.scalar(
            select(func.count(ProjectChecklistItem.id)).where(
                and_(
                    ProjectChecklistItem.due_date < today,
                    ProjectChecklistItem.status.notin_(["done", "skipped"]),
                    ProjectChecklistItem.deleted_at.is_(None),
                )
            )
        ) or 0

        return {
            "total":            total,
            "by_status":        by_status,
            "percent_complete": pct,
            "overdue_count":    overdue,
        }

    # ── Recent activity audit log ─────────────────────────────────────────────

    async def recent_admin_actions(self, limit: int = 50) -> list[dict]:
        """
        Most recently suspended/banned users and orgs — for the
        'Recent Admin Actions' card on the dashboard.
        """
        recent_users = await self.db.execute(
            select(User.id, User.display_name, User.status, User.updated_at)
            .where(User.status.in_([
                AccountStatus.SUSPENDED,
                AccountStatus.BANNED,
                AccountStatus.DEACTIVATED,
            ]))
            .order_by(User.updated_at.desc())
            .limit(limit // 2)
        )
        recent_orgs = await self.db.execute(
            select(Organisation.id, Organisation.display_name, Organisation.status, Organisation.updated_at)
            .where(Organisation.status.in_([
                OrgStatus.SUSPENDED,
                OrgStatus.BANNED,
                OrgStatus.DEACTIVATED,
            ]))
            .order_by(Organisation.updated_at.desc())
            .limit(limit // 2)
        )
        actions = []
        for r in recent_users.all():
            actions.append({
                "entity_type": "user",
                "entity_id":   str(r.id),
                "name":        r.display_name,
                "action":      r.status,
                "at":          r.updated_at.isoformat() if r.updated_at else None,
            })
        for r in recent_orgs.all():
            actions.append({
                "entity_type": "organisation",
                "entity_id":   str(r.id),
                "name":        r.display_name,
                "action":      r.status,
                "at":          r.updated_at.isoformat() if r.updated_at else None,
            })
        return sorted(actions, key=lambda x: x["at"] or "", reverse=True)
