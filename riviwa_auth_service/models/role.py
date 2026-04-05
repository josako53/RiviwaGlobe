"""
models/role.py
═══════════════════════════════════════════════════════════════════════════════
RBAC tables: Permission, Role, RolePermission

ROLE CATEGORIES — the three kinds of role in this system
───────────────────────────────────────────────────────────────────────────────

  PLATFORM   super_admin · admin · moderator
             ↳ Assigned per user via the `user_roles` table.
             ↳ Always global — no org scope.
             ↳ Checked via: user.platform_roles

  CONSUMER   consumer
             ↳ A single reference Role that documents what any active user
               is permitted to do as a buyer/customer:
               browse_listings, place_order, leave_review, send_message …
             ↳ NOT assigned per user via `user_roles`.
               Every active User IS a consumer. No row lookup needed.
             ↳ Checked via: if user.is_active() → load consumer role permissions

  ORG        {org_type}_{role_name}  e.g. business_owner, government_manager
             ↳ Assigned via OrganisationMember.org_role (enum on that table).
             ↳ NOT assigned via `user_roles` — the membership IS the assignment.
             ↳ One set per OrgType so permissions differ across org types.
             ↳ Checked via: user.get_active_membership() → member.org_role

WHY CONSUMER IS A ROLE ROW BUT NOT ASSIGNED PER USER
───────────────────────────────────────────────────────────────────────────────
The consumer Role row lives in this table purely as a permission bundle.
It answers "what CAN a consumer do?" — for documentation, for permission
checks in code, and for the admin UI permission editor.

It is NOT stored in `user_roles` per user because:
  · every active User is a consumer — there is nothing to "grant"
  · it can never be revoked — so it is not a grantable capability
  · creating one row per user is pointless overhead

Permission check for consumer actions:
    consumer_role = get_role_by_name("consumer")          # cached
    if user.is_active() and perm in consumer_role.permissions:
        allow()

SEED DATA
───────────────────────────────────────────────────────────────────────────────
Platform roles:   super_admin, admin, moderator
Consumer role:    consumer
Org roles:        business_owner, business_admin, business_manager, business_member
                  corporate_owner, corporate_admin, corporate_manager, corporate_member
                  government_owner, government_admin, government_manager, government_member
                  ngo_owner, ngo_admin, ngo_manager, ngo_member
                  individual_pro_owner  ← no team; owner only

Permissions (examples):
  platform:  manage_users, suspend_user, ban_user, review_fraud, view_audit_log
  consumer:  browse_listings, place_order, leave_review, send_message, view_own_orders
  org owner: delete_org, transfer_ownership, manage_billing, manage_members,
             manage_settings, create_listing, view_analytics, manage_orders
  org admin: manage_members, manage_settings, manage_billing, view_analytics,
             create_listing, manage_orders
  org mgr:   manage_orders, reply_customers, create_listing, view_orders, view_analytics
  org mbr:   view_orders, view_listings
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Column, DateTime, Enum as SAEnum, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user_role import UserRole


# ─────────────────────────────────────────────────────────────────────────────

class RoleCategory(str, Enum):
    """
    Discriminates which part of the system a Role belongs to.
    Controls where the role is assigned and how it is permission-checked.

    PLATFORM → can be assigned via user_roles  (super_admin, admin, moderator)
    CONSUMER → reference only; never assigned per user via user_roles
    ORG      → used for permission lookup via OrganisationMember; never via user_roles
    """
    PLATFORM = "platform"
    CONSUMER = "consumer"
    ORG      = "org"


# ─────────────────────────────────────────────────────────────────────────────

class Permission(SQLModel, table=True):
    """
    A single named capability code checked at API endpoints.

    Examples:
      "place_order"      — a consumer can place an order
      "manage_members"   — an org admin/owner can add or remove members
      "ban_user"         — a platform admin can ban a user
      "create_listing"   — an org manager can publish a service listing
      "transfer_ownership" — an org owner can hand ownership to another member
    """
    __tablename__ = "permissions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    code: str = Field(
        max_length=100,
        unique=True,
        index=True,
        nullable=False,
        description="Machine-readable key e.g. 'place_order', 'manage_members'",
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    # cascade: removing a Permission removes its RolePermission junction rows
    role_permissions: "RolePermission" = Relationship(
        back_populates="permission",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ─────────────────────────────────────────────────────────────────────────────

class Role(SQLModel, table=True):
    """
    A named bundle of permissions.

    `category` controls how the role is used:
      PLATFORM → assignable via user_roles
      CONSUMER → reference only (never assigned per user)
      ORG      → looked up via OrganisationMember.org_role (never via user_roles)

    Service layer MUST enforce:
      When creating a UserRole row → role.category MUST be PLATFORM.
    """
    __tablename__ = "roles"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    name: str = Field(
        max_length=100,
        unique=True,
        index=True,
        nullable=False,
        description=(
            "Unique role name. Examples: 'consumer', 'super_admin', "
            "'business_owner', 'government_manager'"
        ),
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    category: RoleCategory = Field(
        sa_column=Column(
            SAEnum(RoleCategory, name="role_category"),
            nullable=False,
            index=True,
        ),
        description="platform | consumer | org",
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    # cascade: removing a Role removes its RolePermission junction rows
    role_permissions: "RolePermission" = Relationship(
        back_populates="role",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    # Only populated for PLATFORM roles (consumer + org roles have no user_roles rows)
    user_roles: "UserRole" = Relationship(back_populates="role")


# ─────────────────────────────────────────────────────────────────────────────

class RolePermission(SQLModel, table=True):
    """
    Junction: Role ↔ Permission (many-to-many).
    A role can have many permissions; a permission can belong to many roles.
    """
    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    role_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    permission_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    role:       "Role"       = Relationship(back_populates="role_permissions")
    permission: "Permission" = Relationship(back_populates="role_permissions")
