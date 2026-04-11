"""
models/organisation.py
═══════════════════════════════════════════════════════════════════════════════
Three tables for registered entities and their membership:

  Organisation        — the registered entity (business / corp / govt / NGO)
  OrganisationMember  — junction: User ↔ Org with role + status
  OrganisationInvite  — pending invitations to join an org

═══════════════════════════════════════════════════════════════════════════════
THE COMPLETE IDENTITY MODEL
═══════════════════════════════════════════════════════════════════════════════

One human = one User account. Three independent layers sit on top of it:

  LAYER 1 — Human identity (always present, permanent)
    ─────────────────────────────────────────────────
    The User row IS the person AND the consumer.
    When User.active_org_id is NULL they are in their personal view:
    browsing, ordering, reviewing, messaging — acting as themselves.
    This requires no table. It is unconditional and irrevocable.

  LAYER 2 — Organisation dashboards (zero or many, switchable)
    ──────────────────────────────────────────────────────────
    The same user can own or belong to multiple organisations — just like
    Google Business Profile lets one Google account manage many businesses.
    Each association is one OrganisationMember row.

    Switching to an org dashboard:
        POST /api/v1/auth/switch-org  { "org_id": "<uuid>" }
        Service: validates active OrganisationMember exists for that (user, org)
        DB:      UPDATE users SET active_org_id = '<uuid>'  WHERE id = <user_id>
        JWT:     { "sub": user_id, "org_id": "<uuid>", "org_role": "owner" }

    Returning to personal view:
        POST /api/v1/auth/switch-org  { "org_id": null }
        DB:  UPDATE users SET active_org_id = NULL
        JWT: { "sub": user_id, "org_id": null }

    Source of truth: User.active_org_id (one nullable UUID column).
    No flag on OrganisationMember. No risk of two tables disagreeing.

  LAYER 3 — Platform staff (optional, always-on if granted)
    ───────────────────────────────────────────────────────
    super_admin / admin / moderator stored in user_roles.
    Not a switchable context — always active on top of whichever
    dashboard (personal or org) the user is currently viewing.

═══════════════════════════════════════════════════════════════════════════════
CONCRETE EXAMPLE — John has one account, three hats
═══════════════════════════════════════════════════════════════════════════════

  users row:
    id=john, active_org_id=NULL   ← currently in personal view

  organisation_members rows:
    user_id=john, org_id=smith-logistics, org_role=OWNER,   status=ACTIVE
    user_id=john, org_id=jones-corp,      org_role=ADMIN,   status=ACTIVE
    user_id=john, org_id=city-council,    org_role=MANAGER, status=ACTIVE

  user_roles rows:
    user_id=john, role_id=moderator   ← platform staff

  John's available actions:
    In personal view     → consumer actions (order, review, message)
    In Smith Logistics   → owner actions  (delete org, manage billing, all ops)
    In Jones Corp        → admin actions  (manage members, settings, analytics)
    In City Council      → manager actions (orders, customers, listings)
    Always               → moderator actions (review disputes, warn users)

═══════════════════════════════════════════════════════════════════════════════
ORG MEMBER ROLES
═══════════════════════════════════════════════════════════════════════════════

  OWNER    Created the org or had ownership transferred.
           Full control. Cannot be removed by anyone else.
           Can transfer ownership. Can delete the org.

  ADMIN    Appointed by owner.
           Manage members + settings + billing + analytics.
           Cannot remove the owner. Cannot promote to owner.

  MANAGER  Day-to-day operations.
           Manage orders, reply to customers, create/edit listings.
           Cannot manage members or settings.

  MEMBER   Basic scoped access.
           Read-only or limited task completion.
           Exact permissions differ per OrgType (see role seed data).

═══════════════════════════════════════════════════════════════════════════════
ORG TYPES
═══════════════════════════════════════════════════════════════════════════════

  BUSINESS        Commercial company. List services, receive payments.
  CORPORATE       Enterprise. Bulk features, SLA, dedicated support.
  GOVERNMENT      Gov body. Procurement compliance, strict verification.
  NGO             Non-profit. Reduced platform fees.
  INDIVIDUAL_PRO  Solo professional. Single-person org — no team members.
                  max_members enforced as 1 at the service layer.
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Column, DateTime, Enum as SAEnum, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User
    from models.organisation_extended import (
        OrgLocation,
        OrgContent,
        OrgFAQ,
        OrgBranch,
        OrgService,
    )
    from models.org_project import OrgProject


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class OrgType(str, Enum):
    BUSINESS       = "BUSINESS"
    CORPORATE      = "CORPORATE"
    GOVERNMENT     = "GOVERNMENT"
    NGO            = "NGO"
    INDIVIDUAL_PRO = "INDIVIDUAL_PRO"


class OrgStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"  # awaiting platform admin approval
    ACTIVE               = "ACTIVE"                # verified, fully operational
    SUSPENDED            = "SUSPENDED"             # temporary hold by platform
    BANNED               = "BANNED"                # permanent removal
    DEACTIVATED          = "DEACTIVATED"           # owner-initiated closure


class OrgMemberRole(str, Enum):
    """
    A user's role WITHIN a specific organisation.

    Completely separate from:
      · platform roles  (super_admin / admin / moderator) → stored in user_roles
      · consumer identity → that is the User row itself

    One set of Roles rows per OrgType is seeded in the `roles` table
    (e.g. "business_manager" has different permissions than "government_manager")
    even though both map to OrgMemberRole.MANAGER here.
    """
    OWNER   = "OWNER"    # full control; cannot be removed by others
    ADMIN   = "ADMIN"    # members + settings + billing
    MANAGER = "MANAGER"  # orders + customers + listings
    MEMBER  = "MEMBER"   # read / limited task access


class OrgMemberStatus(str, Enum):
    ACTIVE    = "ACTIVE"     # fully operational member
    INVITED   = "INVITED"    # invite sent, not yet accepted
    SUSPENDED = "SUSPENDED"  # temporarily blocked by owner/admin
    REMOVED   = "REMOVED"    # removed by owner/admin
    LEFT      = "LEFT"       # voluntarily left


class OrgInviteStatus(str, Enum):
    PENDING   = "PENDING"
    ACCEPTED  = "ACCEPTED"
    DECLINED  = "DECLINED"
    EXPIRED   = "EXPIRED"
    CANCELLED = "CANCELLED"


# ─────────────────────────────────────────────────────────────────────────────
# Organisation
# ─────────────────────────────────────────────────────────────────────────────

class Organisation(SQLModel, table=True):
    """
    A registered entity on the platform.

    One User can create MULTIPLE organisations — they are not limited to one
    business. Each org has its own identity, verification, and member list.
    The user who creates the org automatically gets OrgMemberRole.OWNER in
    the corresponding OrganisationMember row.

    Verification:
        Owner submits registration + compliance documents.
        status = PENDING_VERIFICATION, is_verified = False.
        A platform admin reviews and approves:
        status = ACTIVE, is_verified = True, verified_at = now().
        Unverified orgs can exist but CANNOT transact or list services
        (enforced at the service layer).

    Relationships:
        Organisation.created_by  ←→  User.owned_organisations
        Organisation.members     ←→  OrganisationMember.organisation
        Organisation.invites     ←→  OrganisationInvite.organisation
    """
    __tablename__ = "organisations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    legal_name: str = Field(
        max_length=255,
        nullable=False,
        index=True,
        description="Officially registered name used on compliance documents",
    )
    display_name: str = Field(
        max_length=100,
        nullable=False,
        description="Short name shown in the UI switcher and public profile",
    )
    # URL-safe unique handle, e.g. "smith-logistics-ltd"
    slug: str = Field(
        max_length=100,
        unique=True,
        index=True,
        nullable=False,
    )
    logo_url: Optional[str] = Field(default=None, max_length=512, nullable=True)
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # ── Classification ────────────────────────────────────────────────────────
    org_type: OrgType = Field(
        sa_column=Column(
            SAEnum(OrgType, name="org_type"),
            nullable=False,
            index=True,
        ),
    )
    status: OrgStatus = Field(
        default=OrgStatus.PENDING_VERIFICATION,
        sa_column=Column(
            SAEnum(OrgStatus, name="org_status"),
            nullable=False,
            index=True,
        ),
    )

    # ── Contact ───────────────────────────────────────────────────────────────
    website_url:   Optional[str] = Field(default=None, max_length=512, nullable=True)
    support_email: Optional[str] = Field(default=None, max_length=255, nullable=True)
    support_phone: Optional[str] = Field(default=None, max_length=20,  nullable=True)
    country_code:  Optional[str] = Field(default=None, max_length=2,   nullable=True)
    timezone:      Optional[str] = Field(default=None, max_length=50,  nullable=True)

    # ── Compliance ────────────────────────────────────────────────────────────
    registration_number: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Company reg / charity number / tax ID",
    )
    tax_id: Optional[str] = Field(default=None, max_length=100, nullable=True)

    # ── Verification ──────────────────────────────────────────────────────────
    is_verified:    bool = Field(default=False, index=True, nullable=False)
    verified_at:    Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # UUID of the platform admin who approved the verification
    verified_by_id: Optional[uuid.UUID] = Field(default=None, nullable=True)

    # ── Ownership ─────────────────────────────────────────────────────────────
    # RESTRICT: cannot delete a User who is the creator of an org.
    # Transfer ownership first (via POST /orgs/{id}/transfer-ownership),
    # then deactivate the org before the user account can be removed.
    created_by_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    ),
)

    # ── Settings ──────────────────────────────────────────────────────────────
    # 0 = unlimited. INDIVIDUAL_PRO enforced as max=1 at the service layer.
    max_members: int = Field(
        default=0,
        nullable=False,
        description="Max team members; 0 = unlimited",
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
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    created_by: "User" = Relationship(
        back_populates="owned_organisations",
        sa_relationship_kwargs={
            "foreign_keys": "[Organisation.created_by_id]",
        },
    )
    members: "OrganisationMember" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    invites: "OrganisationInvite" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # ── Extended relationships (organisation_extended.py) ─────────────────────
    # OrgLocation: one org → many locations/addresses
    locations: "OrgLocation" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # OrgContent: one org → one content record (1-to-1, enforced by UNIQUE)
    content: "OrgContent" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # OrgFAQ: one org → many FAQ items on its profile page
    faqs: "OrgFAQ" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # OrgBranch: one org → many branches / departments / embassies
    branches: "OrgBranch" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # OrgService: one org → many service/product/program listings
    services: "OrgService" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # OrgProject: one org → many execution projects (construction, programs, etc.)
    projects: "OrgProject" = Relationship(
        back_populates="organisation",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[OrgProject.organisation_id]",
        },
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def is_active(self) -> bool:
        return self.status == OrgStatus.ACTIVE

    def is_operable(self) -> bool:
        """True when verified AND active — can list services / accept payments."""
        return self.status == OrgStatus.ACTIVE and self.is_verified

    def __repr__(self) -> str:
        return f"<Organisation {self.slug!r} [{self.org_type}/{self.status}]>"


# ─────────────────────────────────────────────────────────────────────────────
# OrganisationMember
# ─────────────────────────────────────────────────────────────────────────────

class OrganisationMember(SQLModel, table=True):
    """
    One row = one (User, Organisation) pairing with an internal role.

    A single user can have MANY of these rows — one per org they belong to.
    This is how "one account, multiple businesses" is implemented.

    HOW SWITCHING WORKS
    ────────────────────
    The active org dashboard is tracked by a single field on User:
        User.active_org_id: Optional[uuid.UUID]

    There is NO is_context_active flag on this table. The source of truth
    is always User.active_org_id. This prevents split-brain between two
    tables and makes "which org am I in?" a single O(1) indexed read.

    To switch to this org:
        UPDATE users SET active_org_id = <this.organisation_id>
        Reissue JWT: { "sub": user_id, "org_id": "...", "org_role": "owner" }

    To return to personal view:
        UPDATE users SET active_org_id = NULL
        Reissue JWT: { "sub": user_id, "org_id": null }

    ROLES (org_role) vs PLATFORM ROLES (user_roles)
    ─────────────────────────────────────────────────
    org_role here = role INSIDE this specific org  (owner/admin/manager/member)
    user_roles    = platform-wide staff role       (super_admin/admin/moderator)

    These are completely independent. A platform admin who owns a business has:
        user_roles row:            role_id → admin    (platform)
        organisation_members row:  org_role = OWNER   (their business)

    UNIQUE CONSTRAINT  (user_id, organisation_id)
    A user can only have ONE membership per org. Their role within it
    (org_role) can be changed by the owner/admin without creating a new row.
    """
    __tablename__ = "organisation_members"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "organisation_id",
            name="uq_org_member_user_org",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # CASCADE: removing the User removes their membership rows
    user_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    # CASCADE: removing the Org removes all its membership rows
    organisation_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    # Role within THIS org — completely separate from platform roles
    org_role: OrgMemberRole = Field(
        sa_column=Column(
            SAEnum(OrgMemberRole, name="org_member_role"),
            nullable=False,
            index=True,
        ),
        description="owner | admin | manager | member — role inside this specific org",
    )

    status: OrgMemberStatus = Field(
        default=OrgMemberStatus.ACTIVE,
        sa_column=Column(
            SAEnum(OrgMemberStatus, name="org_member_status"),
            nullable=False,
            index=True,
        ),
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    # NULL for the org creator (they were not invited — they created the org)
    invited_by_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="User who invited this member; null for the org creator",
    )
    joined_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the invite was accepted or the user was directly added",
    )
    removed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
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

    # ── Relationships ─────────────────────────────────────────────────────────
    # back_populates must match exactly:
    #   User.memberships  and  Organisation.members
    user:         "User"         = Relationship(back_populates="memberships")
    organisation: "Organisation" = Relationship(back_populates="members")

    # ── Role-based capability helpers ─────────────────────────────────────────

    def is_active(self) -> bool:
        return self.status == OrgMemberStatus.ACTIVE

    def can_manage_members(self) -> bool:
        """Owner and admin can invite, remove, or change roles of members."""
        return self.org_role in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN)

    def can_manage_settings(self) -> bool:
        """Owner and admin can change org settings, billing, and compliance docs."""
        return self.org_role in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN)

    def can_operate(self) -> bool:
        """Manager and above can handle orders, listings, and customer replies."""
        return self.org_role in (
            OrgMemberRole.OWNER,
            OrgMemberRole.ADMIN,
            OrgMemberRole.MANAGER,
        )

    def can_delete_org(self) -> bool:
        """Only the owner can delete or deactivate the organisation."""
        return self.org_role == OrgMemberRole.OWNER

    def can_transfer_ownership(self) -> bool:
        return self.org_role == OrgMemberRole.OWNER

    def __repr__(self) -> str:
        return (
            f"<OrganisationMember "
            f"user={self.user_id} "
            f"org={self.organisation_id} "
            f"role={self.org_role} [{self.status}]>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# OrganisationInvite
# ─────────────────────────────────────────────────────────────────────────────

class OrganisationInvite(SQLModel, table=True):
    """
    A pending invitation for a User to join an Organisation.

    TWO INVITE MODES
    ─────────────────
    Email invite:    invited_email set, invited_user_id null.
      For someone who may not yet have a platform account.
      When they register/login with that email the invite auto-appears.

    Direct invite:   invited_user_id set, invited_email null.
      For an existing platform user identified by their UUID.

    At least one must be set. Enforced at the service layer.

    INVITE FLOW
    ─────────────
    Owner/Admin sends invite:
        INSERT INTO organisation_invites (status=PENDING, token_hash=sha256(raw))
        Email sent to invitee with a link containing the raw token.

    Invitee clicks the link:
        raw token hashed → looked up by token_hash
        is_valid() checked (PENDING + not expired)
        INSERT INTO organisation_members (status=ACTIVE, org_role=invited_role)
        UPDATE organisation_invites SET status=ACCEPTED, responded_at=now()

    Invitee declines:
        UPDATE organisation_invites SET status=DECLINED, responded_at=now()

    Nobody clicks — daily Celery beat:
        UPDATE organisation_invites SET status=EXPIRED
        WHERE status=PENDING AND expires_at < now()

    OWNERSHIP CANNOT BE INVITED
    ────────────────────────────
    invited_role cannot be OWNER.
    Ownership is only granted via the transfer_ownership endpoint.
    Enforced at the service layer.

    TOKEN SECURITY
    ──────────────
    Same pattern as PasswordResetToken.
    Only sha256(raw_token) is stored. Raw token never touches the DB.
    UNIQUE index on token_hash for O(1) webhook/link lookup.

    Relationships:
        OrganisationInvite.organisation  ←→  Organisation.invites
        OrganisationInvite.invited_by    ←→  User.sent_invites
        OrganisationInvite.invited_user  ←→  User.received_invites
    """
    __tablename__ = "organisation_invites"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # CASCADE: deleting the Org removes its pending invites
    organisation_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    # CASCADE: deleting the sender removes the invite
    invited_by_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    # At least one of these two must be non-null (enforced in service layer)
    invited_user_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)
    invited_email: Optional[str] = Field(
        default=None,
        max_length=255,
        nullable=True,
        index=True,
        description="Email address of the invitee; may not yet have an account",
    )

    # Cannot be OWNER — use transfer_ownership endpoint instead
    invited_role: OrgMemberRole = Field(
        sa_column=Column(
            SAEnum(OrgMemberRole, name="org_member_role"),
            nullable=False,
        ),
        description="admin | manager | member (not owner — use transfer_ownership)",
    )

    status: OrgInviteStatus = Field(
        default=OrgInviteStatus.PENDING,
        sa_column=Column(
            SAEnum(OrgInviteStatus, name="org_invite_status"),
            nullable=False,
            index=True,
        ),
    )

    # sha256(raw_invite_token) — raw token is emailed, never stored
    token_hash: str = Field(
        max_length=64,
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Invite link validity window (typically 7 days from creation)",
    )

    message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Optional personal note from the person sending the invite",
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    responded_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the invitee accepted, declined, or when it was cancelled",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    organisation: "Organisation" = Relationship(back_populates="invites")
    invited_by: "User" = Relationship(
        back_populates="sent_invites",
        sa_relationship_kwargs={
            "foreign_keys": "[OrganisationInvite.invited_by_id]",
        },
    )
    invited_user: "User" = Relationship(
        back_populates="received_invites",
        sa_relationship_kwargs={
            "foreign_keys": "[OrganisationInvite.invited_user_id]",
        },
    )

    # ── Helper ────────────────────────────────────────────────────────────────
    def is_valid(self) -> bool:
        """True when status=PENDING and the invite has not yet expired."""
        if self.status != OrgInviteStatus.PENDING:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

    def __repr__(self) -> str:
        recipient = self.invited_email or str(self.invited_user_id)
        return (
            f"<OrganisationInvite "
            f"org={self.organisation_id} "
            f"to={recipient!r} "
            f"role={self.invited_role} [{self.status}]>"
        )
