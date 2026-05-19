# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/admin_dashboard.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/admin_dashboard.py
════════════════════════════════════════════════════════════════════════════
Platform / system admin dashboard endpoints.

All endpoints require `platform_role = admin` or `super_admin`.
Super-admin-only endpoints (role assignment) are guarded by
`require_platform_role("super_admin")`.

Dashboard sections:
  1. /admin/dashboard/summary        — Top-level KPIs (single call)
  2. /admin/users                    — User list, search, status filter
  3. /admin/users/growth             — Daily registration trend (chart data)
  4. /admin/users/status-breakdown   — Users by AccountStatus (pie chart data)
  5. /admin/users/{id}               — Single user detail + actions
  6. /admin/organisations            — Org list with filters
  7. /admin/organisations/pending    — Verification queue
  8. /admin/organisations/breakdown  — By type × status (chart data)
  9. /admin/organisations/growth     — Daily creation trend
  10. /admin/organisations/{id}      — Single org detail
  11. /admin/projects                — Cross-org project list
  12. /admin/projects/summary        — By status + sector (chart data)
  13. /admin/security/fraud          — Fraud flag summary
  14. /admin/security/flagged-users  — High-risk accounts
  15. /admin/staff                   — Platform staff list
  16. /admin/staff/{user_id}/roles   — Assign / revoke platform role (super_admin)
  17. /admin/checklist-health        — Platform-wide checklist completion
  18. /admin/recent-actions          — Recent admin moderation log

Base URL: https://api.riviwa.com/api/v1
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import DbDep, get_current_user, require_active_user, require_platform_role
from models.user import User
from repositories.admin_dashboard_repository import AdminDashboardRepository
from repositories.user_repository import UserRepository
from repositories.organisation_repository import OrganisationRepository
from services.admin_dashboard_service import AdminDashboardService
from schemas.admin_dashboard import (
    AdminOrgDetail,
    AdminOrgListResponse,
    AdminProjectListResponse,
    AdminProjectSummaryResponse,
    AdminUserDetail,
    AdminUserListResponse,
    AssignRoleRequest,
    BanOrgRequest,
    BanUserRequest,
    ChecklistHealthResponse,
    FlaggedUserListResponse,
    FraudSummaryResponse,
    ModerationActionResponse,
    OrgBreakdownRow,
    OrgGrowthRow,
    OrgMemberDistributionRow,
    PendingVerificationQueueResponse,
    PlatformStaffItem,
    PlatformSummaryResponse,
    RecentAdminActionItem,
    RoleAssignmentResponse,
    SuspendOrgRequest,
    SuspendUserRequest,
    UserGrowthRow,
    UserStatusBreakdownRow,
)

router = APIRouter(prefix="/admin", tags=["Platform Admin Dashboard"])

_admin_guard       = Depends(require_platform_role("admin"))
_superadmin_guard  = Depends(require_platform_role("super_admin"))


def _svc(db: AsyncSession, publisher=None) -> AdminDashboardService:
    return AdminDashboardService(db=db, publisher=publisher)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Summary — single-call platform overview
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard/summary",
    dependencies=[_admin_guard],
    summary="Platform overview — top-level KPIs",
    description=(
        "Returns every KPI needed to render the platform admin home page "
        "in a single call: user counts (total, active, pending, suspended, "
        "banned, new today, new this month), organisation counts "
        "(total, active, pending verification, suspended, banned), project "
        "counts by status, and security flags.\n\n"
        "**Refresh cadence:** suitable for polling every 60 seconds or on "
        "page load. Each sub-count is a direct DB aggregate — no caching."
    ),
)
async def dashboard_summary(db: DbDep) -> PlatformSummaryResponse:
    return await _svc(db).get_platform_summary()


# ─────────────────────────────────────────────────────────────────────────────
# 2–5. Users
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    dependencies=[_admin_guard],
    summary="List all users across the platform",
    description=(
        "Paginated user list with optional filters. "
        "Returns each user's account status, registration date, email, phone, "
        "and platform role (if any). "
        "Use `status=suspended` to see a moderation queue."
    ),
)
async def list_users(
    db:            DbDep,
    status:        Optional[str]  = Query(default=None, description="active | suspended | banned | pending_email | pending_phone | pending_id | channel_registered | deactivated"),
    search:        Optional[str]  = Query(default=None, description="Search by name, email, phone, or username"),
    platform_role: Optional[str]  = Query(default=None, description="Filter by platform role: moderator | admin | super_admin"),
    from_date:     Optional[date] = Query(default=None),
    to_date:       Optional[date] = Query(default=None),
    skip:          int            = Query(default=0,  ge=0),
    limit:         int            = Query(default=50, ge=1, le=200),
) -> AdminUserListResponse:
    return await _svc(db).list_users(
        status=status, search=search, platform_role=platform_role,
        from_date=from_date, to_date=to_date, skip=skip, limit=limit,
    )


@router.get(
    "/users/growth",
    dependencies=[_admin_guard],
    summary="Daily user registration trend (chart data)",
    description=(
        "Returns one row per day for the last `days` days, with registration "
        "count and active count per day. Use this to feed a time-series chart "
        "on the admin dashboard."
    ),
)
async def user_growth_trend(
    db:   DbDep,
    days: int = Query(default=30, ge=7, le=365, description="Number of past days to include"),
) -> List[UserGrowthRow]:
    return await _svc(db).get_user_growth_trend(days=days)


@router.get(
    "/users/status-breakdown",
    dependencies=[_admin_guard],
    summary="Users by account status (pie/bar chart data)",
)
async def user_status_breakdown(db: DbDep) -> List[UserStatusBreakdownRow]:
    return await _svc(db).get_user_status_breakdown()


@router.get(
    "/users/{user_id}",
    dependencies=[_admin_guard],
    summary="Get a single user's full admin view",
    description=(
        "Full user detail for the admin user management screen. "
        "Includes account status, verification flags, fraud score, "
        "org memberships, and platform roles."
    ),
)
async def get_user(user_id: uuid.UUID, db: DbDep) -> AdminUserDetail:
    return await _svc(db).get_user_detail(user_id)


@router.post(
    "/users/{user_id}/suspend",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Suspend a user account (admin)",
)
async def suspend_user(
    user_id: uuid.UUID,
    body:    SuspendUserRequest,
    db:      DbDep,
    admin:   User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).suspend_user(
        user_id=user_id, reason=body.reason, admin_user_id=admin.id
    )


@router.post(
    "/users/{user_id}/ban",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Permanently ban a user account (admin)",
)
async def ban_user(
    user_id: uuid.UUID,
    body:    BanUserRequest,
    db:      DbDep,
    admin:   User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).ban_user(
        user_id=user_id, reason=body.reason, admin_user_id=admin.id
    )


@router.post(
    "/users/{user_id}/reactivate",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Reactivate a suspended or deactivated account (admin)",
)
async def reactivate_user(
    user_id: uuid.UUID,
    db:      DbDep,
    admin:   User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).reactivate_user(user_id=user_id, admin_user_id=admin.id)


# ─────────────────────────────────────────────────────────────────────────────
# 6–10. Organisations
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/organisations",
    dependencies=[_admin_guard],
    summary="List all organisations across the platform",
    description=(
        "Paginated org list with filters for status, type, search, and date range. "
        "Use `status=pending_verification` to see the verification queue."
    ),
)
async def list_organisations(
    db:        DbDep,
    status:    Optional[str]  = Query(default=None, description="active | pending_verification | suspended | banned | deactivated"),
    org_type:  Optional[str]  = Query(default=None, description="business | corporate | government | ngo | individual_pro"),
    search:    Optional[str]  = Query(default=None, description="Search by name or slug"),
    from_date: Optional[date] = Query(default=None),
    to_date:   Optional[date] = Query(default=None),
    skip:      int            = Query(default=0,  ge=0),
    limit:     int            = Query(default=50, ge=1, le=200),
) -> AdminOrgListResponse:
    return await _svc(db).list_organisations(
        status=status, org_type=org_type, search=search,
        from_date=from_date, to_date=to_date, skip=skip, limit=limit,
    )


@router.get(
    "/organisations/pending",
    dependencies=[_admin_guard],
    summary="Organisations awaiting platform verification",
    description=(
        "Returns all organisations in PENDING_VERIFICATION status, oldest first. "
        "This is the verification action queue — review and call POST "
        "/orgs/{org_id}/verify or /ban to process each one."
    ),
)
async def pending_verification_queue(db: DbDep) -> PendingVerificationQueueResponse:
    return await _svc(db).get_pending_verification_queue()


@router.get(
    "/organisations/breakdown",
    dependencies=[_admin_guard],
    summary="Organisations by type and status (chart data)",
)
async def org_breakdown(db: DbDep) -> List[OrgBreakdownRow]:
    return await _svc(db).get_org_breakdown()


@router.get(
    "/organisations/growth",
    dependencies=[_admin_guard],
    summary="Daily organisation creation trend (chart data)",
)
async def org_growth_trend(
    db:   DbDep,
    days: int = Query(default=30, ge=7, le=365),
) -> List[OrgGrowthRow]:
    return await _svc(db).get_org_growth_trend(days=days)


@router.get(
    "/organisations/member-distribution",
    dependencies=[_admin_guard],
    summary="Platform-wide member role distribution",
    description="Count of active org members by role across all organisations.",
)
async def org_member_distribution(db: DbDep) -> List[OrgMemberDistributionRow]:
    return await _svc(db).get_org_member_distribution()


@router.get(
    "/organisations/{org_id}",
    dependencies=[_admin_guard],
    summary="Get a single organisation's admin detail view",
)
async def get_organisation(org_id: uuid.UUID, db: DbDep) -> AdminOrgDetail:
    return await _svc(db).get_org_detail(org_id)


@router.post(
    "/organisations/{org_id}/verify",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Verify an organisation (admin)",
)
async def verify_organisation(
    org_id: uuid.UUID,
    db:     DbDep,
    admin:  User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).verify_organisation(org_id=org_id, admin_user_id=admin.id)


@router.post(
    "/organisations/{org_id}/suspend",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Suspend an organisation (admin)",
)
async def suspend_organisation(
    org_id: uuid.UUID,
    body:   SuspendOrgRequest,
    db:     DbDep,
    admin:  User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).suspend_organisation(
        org_id=org_id, reason=body.reason, admin_user_id=admin.id
    )


@router.post(
    "/organisations/{org_id}/ban",
    dependencies=[_admin_guard],
    status_code=status.HTTP_200_OK,
    summary="Permanently ban an organisation (admin)",
)
async def ban_organisation(
    org_id: uuid.UUID,
    body:   BanOrgRequest,
    db:     DbDep,
    admin:  User = Depends(require_active_user),
) -> ModerationActionResponse:
    return await _svc(db).ban_organisation(
        org_id=org_id, reason=body.reason, admin_user_id=admin.id
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11–12. Projects
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/projects",
    dependencies=[_admin_guard],
    summary="List all projects across the platform",
    description=(
        "Cross-organisation project list. Useful for seeing all active "
        "World Bank / government projects on the platform at a glance."
    ),
)
async def list_projects(
    db:     DbDep,
    status: Optional[str]       = Query(default=None, description="planning | active | paused | completed | cancelled"),
    org_id: Optional[uuid.UUID] = Query(default=None, description="Filter to one organisation"),
    sector: Optional[str]       = Query(default=None),
    region: Optional[str]       = Query(default=None),
    skip:   int                 = Query(default=0,  ge=0),
    limit:  int                 = Query(default=50, ge=1, le=200),
) -> AdminProjectListResponse:
    return await _svc(db).list_projects(
        status=status, org_id=org_id, sector=sector, region=region,
        skip=skip, limit=limit,
    )


@router.get(
    "/projects/summary",
    dependencies=[_admin_guard],
    summary="Platform-wide project summary (chart data)",
    description="Project counts by status and sector, plus total declared budget sum.",
)
async def projects_summary(db: DbDep) -> AdminProjectSummaryResponse:
    return await _svc(db).get_project_summary()


# ─────────────────────────────────────────────────────────────────────────────
# 13–14. Security / Fraud
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/security/fraud",
    dependencies=[_admin_guard],
    summary="Platform-wide fraud assessment summary",
    description=(
        "Breakdown of fraud assessments by risk level (low / medium / high / critical) "
        "with average fraud scores. Also includes the count of accounts in "
        "PENDING_ID status (awaiting government ID verification due to fraud trigger)."
    ),
)
async def fraud_summary(db: DbDep) -> FraudSummaryResponse:
    return await _svc(db).get_fraud_summary()


@router.get(
    "/security/flagged-users",
    dependencies=[_admin_guard],
    summary="High-risk accounts — fraud-flagged user list",
    description=(
        "List of users whose fraud assessment is rated high or critical, "
        "ordered by fraud score descending. Use this to investigate and "
        "decide whether to suspend or ban the account."
    ),
)
async def flagged_users(
    db:         DbDep,
    action:     Optional[str] = Query(default=None, description="review | block"),
    skip:       int           = Query(default=0,  ge=0),
    limit:      int           = Query(default=50, ge=1, le=200),
) -> FlaggedUserListResponse:
    return await _svc(db).list_flagged_users(
        action=action, skip=skip, limit=limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 15–16. Platform staff management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/staff",
    dependencies=[_admin_guard],
    summary="List all platform staff (moderators, admins, super_admins)",
)
async def list_platform_staff(db: DbDep) -> List[PlatformStaffItem]:
    return await _svc(db).list_platform_staff()


@router.post(
    "/staff/{user_id}/roles",
    dependencies=[_superadmin_guard],
    status_code=status.HTTP_200_OK,
    summary="Assign a platform role to a user (super_admin only)",
    description=(
        "Grants a platform role to any user. Only super_admin can do this. "
        "Body: `{\"role\": \"moderator\"}` or `\"admin\"` or `\"super_admin\"`."
    ),
)
async def assign_platform_role(
    user_id: uuid.UUID,
    body:    AssignRoleRequest,
    db:      DbDep,
    admin:   User = Depends(require_active_user),
) -> RoleAssignmentResponse:
    return await _svc(db).assign_platform_role(
        user_id=user_id, role_name=body.role, by_user_id=admin.id
    )


@router.delete(
    "/staff/{user_id}/roles/{role_name}",
    dependencies=[_superadmin_guard],
    status_code=status.HTTP_200_OK,
    summary="Revoke a platform role from a user (super_admin only)",
)
async def revoke_platform_role(
    user_id:   uuid.UUID,
    role_name: str,
    db:        DbDep,
    admin:     User = Depends(require_active_user),
) -> RoleAssignmentResponse:
    return await _svc(db).revoke_platform_role(
        user_id=user_id, role_name=role_name, by_user_id=admin.id
    )


# ─────────────────────────────────────────────────────────────────────────────
# 17. Checklist health
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/checklist-health",
    dependencies=[_admin_guard],
    summary="Platform-wide checklist completion health",
    description=(
        "Aggregated checklist statistics across all projects on the platform. "
        "Shows total items, by-status breakdown, overall completion percentage, "
        "and overdue item count."
    ),
)
async def checklist_health(db: DbDep) -> ChecklistHealthResponse:
    return await _svc(db).get_checklist_health()


# ─────────────────────────────────────────────────────────────────────────────
# 18. Recent admin actions
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/recent-actions",
    dependencies=[_admin_guard],
    summary="Recent admin moderation actions",
    description=(
        "Returns the most recently suspended, banned, or deactivated users "
        "and organisations. Provides a quick audit view of recent admin activity."
    ),
)
async def recent_admin_actions(
    db:    DbDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> List[RecentAdminActionItem]:
    return await _svc(db).get_recent_admin_actions(limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# 19. Platform live statistics
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/platform/stats",
    dependencies=[_admin_guard],
    summary="Platform live statistics — users, orgs, active counts, countries",
    description=(
        "Single-call platform health metrics: total users, active today, "
        "active last 7 days, active last 30 days, new users today, total orgs, "
        "active orgs, new orgs today, distinct countries registered."
    ),
)
async def platform_stats(db: DbDep) -> dict:
    from sqlalchemy import text
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    row = (await db.execute(text("""
        SELECT
            (SELECT COUNT(*)
                FROM users)                                                                      AS total_users,
            (SELECT COUNT(*)
                FROM users WHERE last_login_at >= :today)                                        AS active_today,
            (SELECT COUNT(*)
                FROM users WHERE last_login_at >= NOW() - INTERVAL '7 days')                     AS active_7d,
            (SELECT COUNT(*)
                FROM users WHERE last_login_at >= NOW() - INTERVAL '30 days')                    AS active_30d,
            (SELECT COUNT(*)
                FROM users WHERE created_at >= :today)                                           AS new_users_today,
            (SELECT COUNT(*)
                FROM organisations WHERE deleted_at IS NULL)                                     AS total_orgs,
            (SELECT COUNT(*)
                FROM organisations WHERE deleted_at IS NULL AND status = 'ACTIVE')               AS active_orgs,
            (SELECT COUNT(*)
                FROM organisations WHERE created_at >= :today AND deleted_at IS NULL)            AS new_orgs_today,
            (SELECT COUNT(DISTINCT country_code)
                FROM organisations WHERE country_code IS NOT NULL AND deleted_at IS NULL)        AS countries_count
    """), {"today": today})).mappings().one()
    return dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# 20. Orgs by country
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/platform/by-country",
    dependencies=[_admin_guard],
    summary="Organisations and users grouped by country",
    description=(
        "Aggregates organisations by their country_code. Returns org count, "
        "active/verified orgs, total users, and active users (last 30 days) "
        "per country. Ordered by org count descending."
    ),
)
async def platform_by_country(db: DbDep) -> dict:
    from sqlalchemy import text
    org_rows = (await db.execute(text("""
        SELECT
            COALESCE(country_code, 'UNKNOWN')                   AS country_code,
            COUNT(*)                                             AS org_count,
            COUNT(*) FILTER (WHERE status = 'ACTIVE')           AS active_orgs,
            COUNT(*) FILTER (WHERE is_verified = TRUE)          AS verified_orgs,
            MIN(created_at)::date                                AS first_registered,
            MAX(created_at)::date                                AS last_registered
        FROM organisations
        WHERE deleted_at IS NULL
        GROUP BY COALESCE(country_code, 'UNKNOWN')
        ORDER BY org_count DESC
    """))).mappings().all()

    user_rows = (await db.execute(text("""
        SELECT
            COALESCE(o.country_code, 'UNKNOWN')                 AS country_code,
            COUNT(DISTINCT ur.user_id)                           AS user_count,
            COUNT(DISTINCT ur.user_id) FILTER (
                WHERE u.last_login_at >= NOW() - INTERVAL '30 days'
            )                                                    AS active_users_30d
        FROM user_roles ur
        JOIN organisations o ON ur.org_id::uuid    = o.id
        JOIN users         u ON ur.user_id::uuid   = u.id
        WHERE o.deleted_at IS NULL
        GROUP BY COALESCE(o.country_code, 'UNKNOWN')
    """))).mappings().all()

    user_map = {r["country_code"]: dict(r) for r in user_rows}
    breakdown = []
    for row in org_rows:
        cc = row["country_code"]
        ud = user_map.get(cc, {})
        breakdown.append({
            "country_code":     cc,
            "org_count":        row["org_count"],
            "active_orgs":      row["active_orgs"],
            "verified_orgs":    row["verified_orgs"],
            "user_count":       ud.get("user_count", 0),
            "active_users_30d": ud.get("active_users_30d", 0),
            "first_registered": str(row["first_registered"]),
            "last_registered":  str(row["last_registered"]),
        })
    return {"countries_count": len(breakdown), "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 21. Orgs by region
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/platform/by-region",
    dependencies=[_admin_guard],
    summary="Organisations grouped by administrative region",
    description=(
        "Groups org address records by region field. Filter by country_code to "
        "drill into a specific country's regions (e.g. TZ → Dar es Salaam, Coast, Morogoro)."
    ),
)
async def platform_by_region(
    db:           DbDep,
    country_code: Optional[str] = Query(default=None, description="ISO 2-letter country code, e.g. TZ"),
) -> dict:
    from sqlalchemy import text
    where_parts = ["a.entity_type = 'organisation'", "a.region IS NOT NULL"]
    params: dict = {}
    if country_code:
        where_parts.append("a.country_code = :cc")
        params["cc"] = country_code.upper()
    where = " AND ".join(where_parts)
    rows = (await db.execute(text(f"""
        SELECT
            COALESCE(a.country_code, 'UNKNOWN')  AS country_code,
            a.region,
            COUNT(DISTINCT a.entity_id)           AS org_count
        FROM addresses a
        WHERE {where}
        GROUP BY COALESCE(a.country_code, 'UNKNOWN'), a.region
        ORDER BY org_count DESC
    """), params)).mappings().all()
    return {
        "country_code":  country_code,
        "total_regions": len(rows),
        "breakdown":     [dict(r) for r in rows],
    }
