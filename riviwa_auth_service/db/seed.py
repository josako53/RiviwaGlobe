"""
app/db/seed.py
═══════════════════════════════════════════════════════════════════════════════
Database seeding — initial super-admin user and required platform roles.

Called automatically during lifespan startup via init_db().
All operations are idempotent — safe to run on every container restart.

Seed sequence
─────────────
  1. Ensure the "super_admin" Role row exists in `roles`.
  2. Ensure the admin User row exists in `users`.
  3. Ensure the user_roles junction row exists linking them.

Why is seeding still important?
────────────────────────────────
  - A freshly-created database has no rows in `roles` or `users`.
  - Without a `super_admin` user you cannot call any platform-admin endpoint
    (POST /api/v1/users/{id}/suspend, POST /api/v1/orgs/{id}/verify, etc.)
    because require_platform_role("admin") will deny every request.
  - Seeding is environment-controlled: ADMIN_EMAIL / ADMIN_PASSWORD / names
    are read from settings, which are injected via .env or Docker environment
    variables — so staging and production get different credentials with no
    code change.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import hash_password, normalize_email
from models.role import Role, RoleCategory
from models.user import AccountStatus, User

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_SUPER_ADMIN_ROLE_NAME = "super_admin"
_SUPER_ADMIN_ROLE_DESC = "Full platform access — can manage all users, orgs, and settings."

# SQLAlchemy core table reference for the user_roles junction.
# The ORM class (UserRole) is not yet defined; using the table directly avoids
# importing a missing symbol while remaining fully type-safe at the DB level.
_user_roles_table = sa.Table(
    "user_roles",
    sa.MetaData(),
    sa.Column("id",           sa.UUID,    primary_key=True, default=uuid.uuid4),
    sa.Column("user_id",      sa.UUID,    nullable=False),
    sa.Column("role_id",      sa.UUID,    nullable=False),
    sa.Column("granted_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("granted_by_id", sa.UUID,   nullable=True),
)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Ensure the super_admin Role row exists
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_super_admin_role(db: AsyncSession) -> Role:
    """
    Create the 'super_admin' platform role if it does not exist.
    Returns the Role row (existing or newly created).
    """
    result = await db.execute(
        sa.select(Role).where(Role.name == _SUPER_ADMIN_ROLE_NAME)
    )
    role = result.scalars().first()

    if role:
        log.info("seed.role_exists", role=_SUPER_ADMIN_ROLE_NAME)
        return role

    log.info("seed.creating_role", role=_SUPER_ADMIN_ROLE_NAME)
    role = Role(
        id=uuid.uuid4(),
        name=_SUPER_ADMIN_ROLE_NAME,
        description=_SUPER_ADMIN_ROLE_DESC,
        category=RoleCategory.PLATFORM,
    )
    db.add(role)
    await db.flush()   # assigns role.id without committing
    log.info("seed.role_created", role=_SUPER_ADMIN_ROLE_NAME, role_id=str(role.id))
    return role


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Ensure the admin User row exists
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_admin_user(db: AsyncSession) -> User:
    """
    Create the initial super-admin user if they don't exist.
    Returns the User row (existing or newly created).
    """
    result = await db.execute(
        sa.select(User).where(User.email == settings.ADMIN_EMAIL)
    )
    admin = result.scalars().first()

    if admin:
        log.info("seed.admin_exists", email=settings.ADMIN_EMAIL)
        return admin

    log.info("seed.creating_admin", email=settings.ADMIN_EMAIL)

    email_normalized = normalize_email(settings.ADMIN_EMAIL)

    # Auto-generate a username from the first name + last name
    base_username = (
        f"{settings.ADMIN_FIRST_NAME.lower()}.{settings.ADMIN_LAST_NAME.lower()}"
        .replace(" ", "_")
        .replace("-", "_")
    )

    admin = User(
        id=uuid.uuid4(),
        username=base_username,
        email=settings.ADMIN_EMAIL,
        email_normalized=email_normalized,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        display_name=f"{settings.ADMIN_FIRST_NAME} {settings.ADMIN_LAST_NAME}",
        full_name=f"{settings.ADMIN_FIRST_NAME} {settings.ADMIN_LAST_NAME}",
        status=AccountStatus.ACTIVE,
        is_email_verified=True,
        phone_verified=False,
        id_verified=False,
        fraud_score=0,
        two_factor_enabled=False,
    )
    db.add(admin)
    await db.flush()   # assigns admin.id without committing
    log.info(
        "seed.admin_created",
        email=settings.ADMIN_EMAIL,
        user_id=str(admin.id),
        username=base_username,
    )
    return admin


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Link admin user to super_admin role
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_admin_role_assignment(
    db:      AsyncSession,
    user:    User,
    role:    Role,
) -> None:
    """
    Insert a row into user_roles linking the admin user to super_admin.
    Uses the SQLAlchemy core insert to avoid depending on the missing
    UserRole ORM class.  Skips if the assignment already exists.
    """
    # Check if the assignment already exists
    result = await db.execute(
        sa.text(
            "SELECT 1 FROM user_roles WHERE user_id = :uid AND role_id = :rid LIMIT 1"
        ),
        {"uid": user.id, "rid": role.id},
    )
    if result.first():
        log.info(
            "seed.role_assignment_exists",
            user_id=str(user.id),
            role=role.name,
        )
        return

    log.info(
        "seed.assigning_role",
        user_id=str(user.id),
        role=role.name,
        role_id=str(role.id),
    )
    await db.execute(
        sa.text(
            "INSERT INTO user_roles (id, user_id, role_id, granted_at) "
            "VALUES (:id, :uid, :rid, NOW())"
        ),
        {"id": uuid.uuid4(), "uid": user.id, "rid": role.id},
    )
    log.info("seed.role_assigned", user_id=str(user.id), role=role.name)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def seed_initial_data(db: AsyncSession) -> None:
    """
    Idempotent seed: create the super_admin role and the initial admin user,
    then link them.

    Called inside a single transaction from init_db().
    All writes use db.flush() — commit happens at the caller level so the
    entire seed either succeeds or rolls back atomically.
    """
    log.info("seed.started")

    role  = await _ensure_super_admin_role(db)
    admin = await _ensure_admin_user(db)
    await _ensure_admin_role_assignment(db, admin, role)

    log.info("seed.completed", admin_email=settings.ADMIN_EMAIL)
