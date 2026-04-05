"""
models/user_role.py
─────────────────────────────────────────────────────────────────────────────
Junction table: User ↔ Role  (many-to-many), optionally scoped to an org.

Why `org_id`?
  On a marketplace a user can be a Buyer globally but a Seller only inside
  a specific programme. org_id=None means platform-wide. org_id="seller_prog"
  means the role is scoped to that programme.

Unique constraint
──────────────────
  (user_id, role_id, org_id) together must be unique.
  PostgreSQL treats NULL != NULL for UNIQUE constraints, so two rows with
  org_id=NULL but the same user_id+role_id WOULD both be allowed.
  The service layer must check for existence before inserting a platform-wide row.

Circular import guard
──────────────────────
  user_role.py is imported BY both user.py and role.py via TYPE_CHECKING.
  Runtime imports of User or Role here would create a circular chain:
    user.py → user_role.py → user.py  💥
  The TYPE_CHECKING block breaks that cycle — evaluated only by type checkers.

Aliasing in user.py
────────────────────
  `from models.user_role import UserRole as UserRoleJunction`
  The alias avoids a name collision with any `UserRole` enum elsewhere.

Relationship wiring
────────────────────
  UserRole.user  ←back_populates→  User.platform_roles
  UserRole.role  ←back_populates→  Role.user_roles
─────────────────────────────────────────────────────────────────────────────
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

# ── TYPE_CHECKING guard ───────────────────────────────────────────────────────
# Both User and Role are guarded to prevent the circular import cycle.
# Bare module paths — no app. prefix (PYTHONPATH = riviwa_auth_service/).
if TYPE_CHECKING:
    from models.role import Role
    from models.user import User


class UserRole(SQLModel, table=True):
    """
    Assigns a Role to a User, optionally within an org scope.

    User.platform_roles returns a list of these junction rows.
    To get the actual Role objects:
        [ur.role for ur in user.platform_roles]

    Only PLATFORM roles are stored here (super_admin, admin, moderator).
    Consumer roles: implicit for any ACTIVE user — no row needed.
    Org roles: live on OrganisationMember.org_role, not here.
    """
    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "org_id", name="uq_user_role_org"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── FK → users ────────────────────────────────────────────────────────────
    # CASCADE: removing a User removes all their UserRole rows automatically.
    # ondelete must be on ForeignKey(), not passed via sa_column_kwargs —
    # the latter raises TypeError in SQLAlchemy 2.x.
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # ── FK → roles ────────────────────────────────────────────────────────────
    # CASCADE: removing a Role removes all UserRole assignments for that role.
    role_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # ── Optional org scope ────────────────────────────────────────────────────
    # None     = platform-wide  (e.g. "admin" applies everywhere)
    # non-None = scoped to that org/programme identifier
    org_id: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
    )

    # ── Audit columns ─────────────────────────────────────────────────────────
    granted_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    # Which admin user granted this role. NULL for system/seed assignments.
    granted_by_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # back_populates MUST exactly match the attribute name on the other model:
    #   User.platform_roles  declares  back_populates="user"
    #     → so this side is named `user` and points back to "platform_roles"
    #   Role.user_roles      declares  back_populates="role"
    #     → so this side is named `role` and points back to "user_roles"
    user: Optional["User"] = Relationship(back_populates="platform_roles")
    role: Optional["Role"] = Relationship(back_populates="user_roles")
