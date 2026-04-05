# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  models/user.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/user.py
═══════════════════════════════════════════════════════════════════════════════
Core User table — one row = one human being, permanently.

═══════════════════════════════════════════════════════════════════════════════
THE RULES
═══════════════════════════════════════════════════════════════════════════════

  ONE ACCOUNT PER HUMAN
  ──────────────────────
  Enforced by three UNIQUE constraints: email, email_normalized, phone_number.
  Further enforced at registration time by the fraud detection layer:
  device fingerprint, IP velocity, behavioral signals, government ID hash.
  A human cannot have two User rows.

  THE USER IS THE CONSUMER — NOT A ROLE
  ───────────────────────────────────────
  Every active User can perform consumer actions: browse listings, place
  orders, write reviews, send messages, view their own order history.
  This is unconditional and irrevocable. It cannot be granted or removed.

  The "consumer" Role row exists in the `roles` table purely as a
  permission reference — it documents what a consumer is allowed to do
  and gives a named bundle for the permission-check code to load.
  No row is ever created in `user_roles` for consumer. The check is:

      consumer_role = get_role_by_name("consumer")    # cached
      if user.is_active() and perm in consumer_role.permissions:
          allow()

  ONE ACCOUNT — MULTIPLE BUSINESSES (like Google Business Profile)
  ─────────────────────────────────────────────────────────────────
  The same user can register or join any number of organisations.
  Each is one OrganisationMember row. The user never creates a second account.

      user.memberships  →  all orgs this user belongs to, with their role in each
      user.owned_organisations  →  orgs where this user is the creator

  DASHBOARD SWITCHING (not identity switching)
  ─────────────────────────────────────────────
  The user is ALWAYS a consumer. What changes is which DASHBOARD they are
  currently operating:

      active_org_id = NULL   →  personal/consumer view (default after login)
      active_org_id = UUID   →  operating that org's dashboard

  Switching:
      POST /api/v1/auth/switch-org  { "org_id": "<uuid>" }
      → service validates active OrganisationMember exists for (user, org)
      → UPDATE users SET active_org_id = <uuid>
      → reissue JWT: { "sub": user_id, "org_id": "<uuid>", "org_role": "owner" }

  Back to personal:
      POST /api/v1/auth/switch-org  { "org_id": null }
      → UPDATE users SET active_org_id = NULL
      → reissue JWT: { "sub": user_id, "org_id": null }

  PLATFORM STAFF (always-on, not a switchable context)
  ──────────────────────────────────────────────────────
  super_admin / admin / moderator are stored in user_roles.
  They are additional capabilities that are always present on top of
  whichever view (personal or org) the user is currently in.
  A moderator who owns a business can moderate content while viewing
  their business dashboard. No "switching to platform mode" needed.

═══════════════════════════════════════════════════════════════════════════════
JWT PAYLOAD REFERENCE
═══════════════════════════════════════════════════════════════════════════════

  After login (personal view):
    { "sub": "user-uuid", "org_id": null,          "platform_role": null }

  After switch-org to "Smith Logistics" (owner):
    { "sub": "user-uuid", "org_id": "smith-uuid",  "platform_role": null,
      "org_role": "owner" }

  Platform admin, personal view:
    { "sub": "user-uuid", "org_id": null,          "platform_role": "admin" }

  Platform moderator, operating their own business:
    { "sub": "user-uuid", "org_id": "smith-uuid",  "platform_role": "moderator",
      "org_role": "owner" }

═══════════════════════════════════════════════════════════════════════════════
RELATIONSHIPS
═══════════════════════════════════════════════════════════════════════════════

  platform_roles       → UserRole rows         (super_admin/admin/moderator only)
  memberships          → OrganisationMember     (all org access)
  owned_organisations  → Organisation           (orgs this user created)
  sent_invites         → OrganisationInvite     (invites sent to others)
  received_invites     → OrganisationInvite     (invites addressed to this user)
  addresses            → Address                (billing / shipping / home)
  password_reset_tokens → PasswordResetToken
  fingerprints         → DeviceFingerprint      (fraud detection)
  fraud_assessments    → FraudAssessment        (fraud detection)
  id_verifications     → IDVerification         (gov ID check)
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.address import Address
    from models.fraud import DeviceFingerprint, FraudAssessment, IDVerification
    from models.organisation import Organisation, OrganisationInvite, OrganisationMember
    from models.organisation_extended import OrgBranchManager, OrgServicePersonnel
    from models.password_reset import PasswordResetToken

    # Before: from models.user_role import UserRole as UserRoleJunction
    from models.user_role import UserRole


# ─────────────────────────────────────────────────────────────────────────────

class AccountStatus(str, Enum):
    """
    Registration and account lifecycle states.

    Happy path:        PENDING_EMAIL → (verify email) → ACTIVE
    With phone step:   PENDING_EMAIL → PENDING_PHONE  → (verify SMS) → ACTIVE
    With fraud trigger:   ACTIVE → (score spikes) → PENDING_ID
                          → (gov ID approved) → ACTIVE
    Admin actions:     ACTIVE → SUSPENDED  (temporary; user can appeal)
                       ACTIVE → BANNED     (permanent)
    User-initiated:    ACTIVE → DEACTIVATED (soft delete)
    """
    PENDING_EMAIL  = "pending_email"
    PENDING_PHONE  = "pending_phone"
    PENDING_ID     = "pending_id"
    CHANNEL_REGISTERED = "channel_registered"  # registered via SMS/WhatsApp/Call — no password set yet
    ACTIVE         = "active"
    SUSPENDED      = "suspended"
    BANNED         = "banned"
    DEACTIVATED    = "deactivated"


# ─────────────────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )

    # ── Identity — all UNIQUE to enforce one-account-per-human ───────────────
    username: str = Field(
        max_length=50,
        unique=True,
        index=True,
        nullable=False,
    )
    # NULL for phone-only registrations — PostgreSQL allows multiple NULLs on
    # a UNIQUE index, so phone-only users don't collide with each other here.
    # Empty string "" is NOT used — it would collide on the unique constraint.
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        unique=True,
        index=True,
        nullable=True,
    )
    # Catches gmail dot-tricks and +aliases:
    #   j.o.h.n+work@gmail.com  normalises to  john@gmail.com
    # If this normalised form already exists → duplicate account → block.
    # NULL for phone-only registrations (same reasoning as email above).
    email_normalized: Optional[str] = Field(
        default=None,
        max_length=255,
        unique=True,
        index=True,
        nullable=True,
        description="Normalised email — dots stripped, + aliases removed. NULL for phone-only users.",
    )
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        unique=True,
        index=True,
        nullable=True,
        description="E.164 format e.g. +12125551234",
    )
    phone_verified: bool = Field(default=False, nullable=False)

    # ── Registration source ────────────────────────────────────────────────────
    # Tracks how the user account was first created.
    # "web" / "mobile" / "sms" / "whatsapp" / "phone_call" / "social" / "admin"
    registration_source: Optional[str] = Field(
        default="web",
        max_length=30,
        nullable=True,
        description=(
            "How this account was created. "
            "channel-registered accounts (sms/whatsapp/phone_call) start with "
            "status=CHANNEL_REGISTERED and no password. "
            "They upgrade to ACTIVE when the PAP logs in and sets a password."
        ),
    )

    # NULL for OAuth/SSO-only accounts (no password set)
    hashed_password: Optional[str] = Field(
        default=None,
        max_length=512,
        nullable=True,
        description="Argon2id hash; null for OAuth-only accounts",
    )

    # ── Personal profile ──────────────────────────────────────────────────────
    # The user's OWN details — not tied to any org.
    # Each org has its own display_name and logo on the Organisation row.
    display_name: Optional[str] = Field(default=None, max_length=100, nullable=True)
    full_name:    Optional[str] = Field(default=None, max_length=200, nullable=True)
    avatar_url:   Optional[str] = Field(default=None, max_length=512, nullable=True)
    country_code: Optional[str] = Field(default=None, max_length=2,   nullable=True)
    language: str = Field(
        default="en",
        max_length=10,
        nullable=False,
        description="BCP-47 language tag e.g. 'en', 'sw', 'fr'",
    )

    # ── Account status ────────────────────────────────────────────────────────
    status: AccountStatus = Field(
        default=AccountStatus.PENDING_EMAIL,
        sa_column=Column(
            SAEnum(AccountStatus, name="account_status"),
            nullable=False,
            index=True,
        ),
    )

    # ── Active org dashboard ──────────────────────────────────────────────────
    # NULL  = user is in their personal/consumer view (default state)
    # UUID  = user is currently operating this organisation's dashboard
    #
    # This is the ONLY mechanism for dashboard switching.
    # The service layer validates that an active OrganisationMember row
    # exists for (user_id, active_org_id) before setting this field.
    # The JWT always mirrors this value + org_role from OrganisationMember.
    #
    # No FK constraint at the DB level — the service layer owns the validation.
    # This avoids FK deferral complexity and allows atomic JWT + DB updates.
    active_org_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "NULL = personal/consumer view. "
            "UUID = currently operating that org's dashboard."
        ),
    )

    # ── Email verification ────────────────────────────────────────────────────
    is_email_verified: bool = Field(default=False, nullable=False)
    email_verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # ── OAuth / SSO ───────────────────────────────────────────────────────────
    oauth_provider:    Optional[str] = Field(default=None, max_length=30,  nullable=True)
    oauth_provider_id: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # ── Security ──────────────────────────────────────────────────────────────
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Locked until this UTC time after too many failed logins",
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_login_ip: Optional[str] = Field(default=None, max_length=45, nullable=True)
    two_factor_enabled: bool       = Field(default=False, nullable=False)
    two_factor_secret:  Optional[str] = Field(default=None, max_length=64, nullable=True)

    # ── Fraud / identity verification ─────────────────────────────────────────
    id_verified: bool = Field(
        default=False,
        index=True,
        nullable=False,
        description="True once government ID verification approved",
    )
    id_verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    fraud_score: int = Field(
        default=0,
        nullable=False,
        description="Latest aggregate fraud score 0–100 (set by ScoringEngine)",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Set on soft-delete (DEACTIVATED); null while account is live",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    # Platform staff assignments (super_admin / admin / moderator).
    # Empty list → regular user with no elevated platform access.
    platform_roles: list["UserRole"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # All org memberships — one row per org this user belongs to.
    # org_role on each row = their role within that specific org.
    memberships: list["OrganisationMember"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # Orgs this user created. No cascade — deleting a user who owns an org
    # is BLOCKED by the RESTRICT FK on Organisation.created_by_id.
    # Transfer ownership first, then deactivate the org, then delete the user.
    owned_organisations: list["Organisation"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "foreign_keys": "[Organisation.created_by_id]",
        },
    )

    # Org invites this user sent to others
    sent_invites: list["OrganisationInvite"] = Relationship(
        back_populates="invited_by",
        sa_relationship_kwargs={
            "foreign_keys": "[OrganisationInvite.invited_by_id]",
        },
    )

    # Org invites addressed to this user (by email or direct user_id)
    received_invites: list["OrganisationInvite"] = Relationship(
        back_populates="invited_user",
        sa_relationship_kwargs={
            "foreign_keys": "[OrganisationInvite.invited_user_id]",
        },
    )

    # Personal addresses (billing / shipping / home)
    addresses: list["Address"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[Address.user_id]",
        },
    )

    # Branch manager/director assignments (organisation_extended.py)
    managed_branches: list["OrgBranchManager"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # Service / program / product leadership + supervision roles
    service_roles: list["OrgServicePersonnel"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # One-time password reset tokens
    password_reset_tokens: list["PasswordResetToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # Fraud detection
    fingerprints: list["DeviceFingerprint"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    fraud_assessments: list["FraudAssessment"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    id_verifications: list["IDVerification"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # ── Domain helpers ────────────────────────────────────────────────────────

    def is_active(self) -> bool:
        """Account is fully onboarded and operational."""
        return self.status == AccountStatus.ACTIVE

    def is_locked(self) -> bool:
        """Temporarily locked due to too many failed login attempts."""
        if self.locked_until is None:
            return False
        locked = self.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked

    def requires_id_verification(self) -> bool:
        """Fraud score triggered a government ID check requirement."""
        return self.status == AccountStatus.PENDING_ID

    # ── Dashboard helpers ─────────────────────────────────────────────────────

    def is_in_org_dashboard(self) -> bool:
        """True when the user is currently operating an org dashboard."""
        return self.active_org_id is not None

    def is_in_personal_view(self) -> bool:
        """True when the user is in their personal/consumer view."""
        return self.active_org_id is None

    def get_active_membership(self) -> Optional["OrganisationMember"]:
        """
        Returns the OrganisationMember row for the current org dashboard.
        Returns None when in personal view or when memberships are not loaded.

        Typical usage at an org-scoped endpoint:
            member = user.get_active_membership()
            if not member:
                raise NotInOrgDashboard()
            if not member.can_operate():
                raise PermissionDenied()
        """
        if self.active_org_id is None:
            return None
        for m in self.memberships:
            if m.organisation_id == self.active_org_id and m.is_active():
                return m
        return None

    def get_membership_for(self, org_id: uuid.UUID) -> Optional["OrganisationMember"]:
        """
        Returns the active membership row for a specific org.
        Used by the switch-org service to validate a switch request.
        """
        for m in self.memberships:
            if m.organisation_id == org_id and m.is_active():
                return m
        return None

    def is_platform_staff(self) -> bool:
        """True if the user holds any platform-level role."""
        return len(self.platform_roles) > 0

    def get_platform_role_names(self) -> list[str]:
        """
        Names of all platform roles held by this user.
        Usually zero or one entry.
        Example: ["moderator"] or ["super_admin"]
        """
        return [ur.role.name for ur in self.platform_roles if ur.role]

    def available_org_dashboards(self) -> list["OrganisationMember"]:
        """
        All org dashboards this user can switch into (active memberships only).
        Sorted by org display_name for the UI switcher dropdown.
        """
        active = [m for m in self.memberships if m.is_active()]
        active.sort(
            key=lambda m: (
                m.organisation.display_name if m.organisation else ""
            )
        )
        return active

    def __repr__(self) -> str:
        view = f"org:{self.active_org_id}" if self.active_org_id else "personal"
        return f"<User {self.username!r} [{self.status}] view={view}>"