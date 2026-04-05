# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  schemas/admin_dashboard.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/admin_dashboard.py
════════════════════════════════════════════════════════════════════════════
Pydantic schemas for all platform admin dashboard endpoints.

Sections
────────
  1.  Platform summary (home page KPIs)
  2.  Users — list, detail, growth trend, status breakdown
  3.  Organisations — list, detail, pending queue, breakdown, growth
  4.  Projects — list, summary
  5.  Security / fraud — summary, flagged-user list
  6.  Platform staff — list, role assignment
  7.  Checklist health
  8.  Recent admin actions
  9.  Moderation action request bodies

Design notes
────────────
  · All response schemas use `model_config = ConfigDict(from_attributes=True)`
    so they work directly with SQLAlchemy ORM objects via `model_validate`.
  · Enum fields stored as strings in the DB are returned as strings here so
    the API layer stays decoupled from the SQLAlchemy enum types.
  · Where a DB model field may be None the schema field is Optional with a
    default of None so validation never raises on missing fields.
  · Every paginated response uses `PaginatedAdminResponse[T]` — a typed
    generic that includes total, returned, skip, limit, and the items list.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# Generic paginated wrapper
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedAdminResponse(BaseModel, Generic[T]):
    """Standard paginated envelope for all admin list endpoints."""
    model_config = ConfigDict(from_attributes=False)

    total:    int
    returned: int
    skip:     int
    limit:    int
    items:    List[T]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Platform summary
# ─────────────────────────────────────────────────────────────────────────────

class UserSummaryBlock(BaseModel):
    """User counts for the platform summary card."""
    model_config = ConfigDict(from_attributes=False)

    total:          int
    active:         int
    pending:        int
    suspended:      int
    banned:         int
    new_this_month: int
    new_today:      int


class OrgSummaryBlock(BaseModel):
    """Organisation counts for the platform summary card."""
    model_config = ConfigDict(from_attributes=False)

    total:                 int
    active:                int
    pending_verification:  int
    suspended:             int
    banned:                int
    deactivated:           int


class ProjectSummaryBlock(BaseModel):
    """Project counts for the platform summary card."""
    model_config = ConfigDict(from_attributes=False)

    total:     int
    active:    int
    by_status: Dict[str, int]


class SecuritySummaryBlock(BaseModel):
    """Security KPIs for the platform summary card."""
    model_config = ConfigDict(from_attributes=False)

    high_risk_fraud_flags: int


class PlatformSummaryResponse(BaseModel):
    """
    Top-level platform overview returned by GET /admin/dashboard/summary.

    All four blocks are computed in a single repository call so the
    frontend can render the full home page with one HTTP request.
    """
    model_config = ConfigDict(from_attributes=False)

    generated_at:  str
    users:         UserSummaryBlock
    organisations: OrgSummaryBlock
    projects:      ProjectSummaryBlock
    security:      SecuritySummaryBlock

    @classmethod
    def from_dict(cls, d: dict) -> "PlatformSummaryResponse":
        return cls(
            generated_at  = d["generated_at"],
            users         = UserSummaryBlock(**d["users"]),
            organisations = OrgSummaryBlock(**d["organisations"]),
            projects      = ProjectSummaryBlock(**d["projects"]),
            security      = SecuritySummaryBlock(**d["security"]),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Users
# ─────────────────────────────────────────────────────────────────────────────

class AdminUserListItem(BaseModel):
    """
    One row in the admin user list.

    Includes the fields needed to identify the user, assess their status,
    and decide whether to take a moderation action — without exposing
    password hash or internal security tokens.
    """
    model_config = ConfigDict(from_attributes=False)

    id:            uuid.UUID
    display_name:  Optional[str] = None
    email:         Optional[str] = None
    phone:         Optional[str] = None
    username:      Optional[str] = None
    status:        str
    created_at:    Optional[str] = None
    last_login_at: Optional[str] = None
    fraud_score:   Optional[float] = None


class AdminUserDetail(BaseModel):
    """
    Full user detail for the admin user management screen.
    Returned by GET /admin/users/{id}.
    """
    model_config = ConfigDict(from_attributes=False)

    id:                     uuid.UUID
    display_name:           Optional[str]  = None
    email:                  Optional[str]  = None
    phone:                  Optional[str]  = None
    username:               Optional[str]  = None
    status:                 str
    email_verified:         bool           = False
    phone_verified:         bool           = False
    fraud_score:            Optional[float] = None
    language:               Optional[str]  = None
    created_at:             Optional[str]  = None
    last_login_at:          Optional[str]  = None
    failed_login_attempts:  int            = 0
    platform_roles:         List[str]      = []


class UserGrowthRow(BaseModel):
    """One day's registration data for the growth trend chart."""
    model_config = ConfigDict(from_attributes=False)

    date:          str   # "YYYY-MM-DD"
    registrations: int
    active:        int


class UserStatusBreakdownRow(BaseModel):
    """User count per AccountStatus for a pie/bar chart."""
    model_config = ConfigDict(from_attributes=False)

    status: str
    count:  int


class AdminUserListResponse(PaginatedAdminResponse[AdminUserListItem]):
    """Paginated user list response."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 3. Organisations
# ─────────────────────────────────────────────────────────────────────────────

class AdminOrgListItem(BaseModel):
    """One row in the admin organisation list."""
    model_config = ConfigDict(from_attributes=False)

    id:          uuid.UUID
    name:        str
    slug:        str
    org_type:    str
    status:      str
    is_verified: bool          = False
    created_at:  Optional[str] = None


class AdminOrgDetail(BaseModel):
    """
    Full organisation detail for the admin org management screen.
    Returned by GET /admin/organisations/{id}.
    """
    model_config = ConfigDict(from_attributes=False)

    id:            uuid.UUID
    name:          str
    slug:          str
    org_type:      str
    status:        str
    is_verified:   bool           = False
    country:       Optional[str]  = None
    contact_email: Optional[str]  = None
    contact_phone: Optional[str]  = None
    created_at:    Optional[str]  = None
    member_count:  int            = 0


class PendingOrgItem(BaseModel):
    """One item in the verification queue."""
    model_config = ConfigDict(from_attributes=False)

    id:         uuid.UUID
    name:       str
    slug:       str
    org_type:   str
    created_at: Optional[str] = None


class PendingVerificationQueueResponse(BaseModel):
    """Response for GET /admin/organisations/pending."""
    model_config = ConfigDict(from_attributes=False)

    count: int
    items: List[PendingOrgItem]


class OrgBreakdownRow(BaseModel):
    """One row in the org type × status breakdown."""
    model_config = ConfigDict(from_attributes=False)

    org_type: str
    status:   str
    count:    int


class OrgGrowthRow(BaseModel):
    """One day in the org creation trend."""
    model_config = ConfigDict(from_attributes=False)

    date:    str   # "YYYY-MM-DD"
    created: int


class OrgMemberDistributionRow(BaseModel):
    """Member count per org role across the platform."""
    model_config = ConfigDict(from_attributes=False)

    role:  str
    count: int


class AdminOrgListResponse(PaginatedAdminResponse[AdminOrgListItem]):
    """Paginated organisation list response."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 4. Projects
# ─────────────────────────────────────────────────────────────────────────────

class AdminProjectListItem(BaseModel):
    """One row in the admin cross-org project list."""
    model_config = ConfigDict(from_attributes=False)

    id:           uuid.UUID
    name:         str
    code:         Optional[str]  = None
    org_id:       uuid.UUID
    status:       str
    sector:       Optional[str]  = None
    region:       Optional[str]  = None
    lga:          Optional[str]  = None
    total_budget: Optional[float] = None
    start_date:   Optional[str]  = None
    end_date:     Optional[str]  = None


class AdminProjectSummaryResponse(BaseModel):
    """Platform-wide project summary for GET /admin/projects/summary."""
    model_config = ConfigDict(from_attributes=False)

    by_status:        Dict[str, int]
    by_sector:        Dict[str, int]
    total_budget_sum: float


class AdminProjectListResponse(PaginatedAdminResponse[AdminProjectListItem]):
    """Paginated cross-org project list response."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 5. Security / fraud
# ─────────────────────────────────────────────────────────────────────────────

class FraudRiskLevelBlock(BaseModel):
    """Stats for one risk level bucket."""
    model_config = ConfigDict(from_attributes=False)

    count:     int
    avg_score: float


class FraudSummaryResponse(BaseModel):
    """Platform-wide fraud assessment summary."""
    model_config = ConfigDict(from_attributes=False)

    by_action:                               Dict[str, FraudRiskLevelBlock]
    accounts_pending_id_verification:        int

    @classmethod
    def from_dict(cls, d: dict) -> "FraudSummaryResponse":
        return cls(
            by_action={
                k: FraudRiskLevelBlock(**v)
                for k, v in d.get("by_action", {}).items()
            },
            accounts_pending_id_verification=d.get("accounts_pending_id_verification", 0),
        )


class FlaggedUserItem(BaseModel):
    """
    One high-risk user in the fraud-flagged user list.
    Used in the security review queue.
    """
    model_config = ConfigDict(from_attributes=False)

    user_id:      uuid.UUID
    display_name: Optional[str]  = None
    email:        Optional[str]  = None
    phone:        Optional[str]  = None
    user_status:  str
    fraud_score:  Optional[float] = None
    risk_level:   Optional[str]   = None
    assessed_at:  Optional[str]   = None


class FlaggedUserListResponse(PaginatedAdminResponse[FlaggedUserItem]):
    """Paginated flagged-user list response."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 6. Platform staff
# ─────────────────────────────────────────────────────────────────────────────

class PlatformStaffItem(BaseModel):
    """One platform staff member in the staff list."""
    model_config = ConfigDict(from_attributes=False)

    user_id:       uuid.UUID
    display_name:  Optional[str] = None
    email:         Optional[str] = None
    phone:         Optional[str] = None
    platform_role: str
    status:        str


class AssignRoleRequest(BaseModel):
    """Body for POST /admin/staff/{user_id}/roles."""
    role: str = Field(description="moderator | admin | super_admin")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("moderator", "admin", "super_admin"):
            raise ValueError("role must be moderator, admin, or super_admin")
        return v


class RoleAssignmentResponse(BaseModel):
    """Response after assigning or revoking a platform role."""
    model_config = ConfigDict(from_attributes=False)

    message:  str
    user_id:  uuid.UUID
    role:     str


# ─────────────────────────────────────────────────────────────────────────────
# 7. Checklist health
# ─────────────────────────────────────────────────────────────────────────────

class ChecklistHealthResponse(BaseModel):
    """
    Platform-wide checklist completion health.
    Returned by GET /admin/checklist-health.
    """
    model_config = ConfigDict(from_attributes=False)

    total:            int
    by_status:        Dict[str, int]
    percent_complete: float
    overdue_count:    int


# ─────────────────────────────────────────────────────────────────────────────
# 8. Recent admin actions
# ─────────────────────────────────────────────────────────────────────────────

class RecentAdminActionItem(BaseModel):
    """
    One entry in the recent admin moderation log.
    Covers both user and organisation actions.
    """
    model_config = ConfigDict(from_attributes=False)

    entity_type: str          # "user" | "organisation"
    entity_id:   uuid.UUID
    name:        Optional[str] = None
    action:      str           # the status that was set: suspended | banned | deactivated
    at:          Optional[str] = None   # ISO datetime


# ─────────────────────────────────────────────────────────────────────────────
# 9. Moderation request bodies
# ─────────────────────────────────────────────────────────────────────────────

class SuspendUserRequest(BaseModel):
    """
    Body for POST /admin/users/{id}/suspend.
    Reason is optional but strongly recommended for audit trail.
    """
    reason: Optional[str] = Field(
        default=None,
        description="Human-readable reason for suspension. Stored in audit log.",
    )


class BanUserRequest(BaseModel):
    """
    Body for POST /admin/users/{id}/ban.
    Reason is required for permanent ban actions.
    """
    reason: str = Field(
        description="Required justification for the permanent ban.",
    )


class SuspendOrgRequest(BaseModel):
    """Body for POST /admin/organisations/{id}/suspend."""
    reason: Optional[str] = Field(default=None)


class BanOrgRequest(BaseModel):
    """Body for POST /admin/organisations/{id}/ban."""
    reason: str = Field(description="Required justification for the permanent ban.")


class ModerationActionResponse(BaseModel):
    """Standard response for all moderation actions (suspend, ban, reactivate, verify)."""
    model_config = ConfigDict(from_attributes=False)

    message:     str
    entity_type: str        # "user" | "organisation"
    entity_id:   uuid.UUID
    new_status:  str
    action_at:   str        # ISO datetime
