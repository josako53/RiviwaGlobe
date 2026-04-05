"""
app/db/init_db.py
═══════════════════════════════════════════════════════════════════════════════
Database initialisation: create all tables, then seed required data.

Called once during the FastAPI lifespan startup (app/main.py).

Retry logic
────────────
  PostgreSQL inside Docker takes a few seconds to become ready after the
  container starts.  DNS may also not resolve immediately when multiple
  services start in parallel.  The retry loop with exponential back-off
  handles both cases without requiring external health-check scripts.

  Defaults:  max_retries=5, initial_delay=2 s, back-off factor=2
  → waits: 2 s → 4 s → 8 s → 16 s before giving up (total ≈ 30 s)

Table creation strategy
────────────────────────
  Uses SQLModel.metadata.create_all() in a synchronous context via
  conn.run_sync().  This is schema-only, NOT migrations.

  For production you should run Alembic migrations instead:
      alembic upgrade head

  create_all() is safe here because:
  - checkfirst=True is the default — existing tables are not touched.
  - It's only called on startup, not in the hot path.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel

from db.seed import seed_initial_data
from db.session import AsyncSessionLocal, engine

# Import every model class explicitly so SQLModel.metadata sees all 27 tables
# before create_all() runs. Import order follows FK dependencies (same as base.py).
# Missing an import here = that table is silently skipped by create_all().

# 1. Roles and permissions (no FK deps)
from models.role import Permission, Role, RolePermission          # noqa: F401

# 2. Core user (no FK deps on other app models)
from models.user import User                                       # noqa: F401

# 3. Organisations (FK → users)
from models.organisation import (                                  # noqa: F401
    Organisation,
    OrganisationMember,
    OrganisationInvite,
)

# 4. Platform staff role assignments (FK → users + roles)
from models.user_role import UserRole                              # noqa: F401

# 5. Personal addresses (FK → users)
from models.address import Address                                 # noqa: F401

# 6. Password reset tokens (FK → users)
from models.password_reset import PasswordResetToken               # noqa: F401

# 7. Fraud detection (FK → users; FraudAssessment also FK → id_verifications)
from models.fraud import (                                         # noqa: F401
    BehavioralSession,
    DeviceFingerprint,
    FraudAssessment,
    IDVerification,
    IPRecord,
)

# 8. Extended org content, branches, services (FK → organisations + users)
from models.organisation_extended import (                         # noqa: F401
    OrgBranch,
    OrgBranchManager,
    OrgBranchService,
    OrgContent,
    OrgFAQ,
    OrgLocation,
    OrgService,
    OrgServiceFAQ,
    OrgServiceLocation,
    OrgServiceMedia,
    OrgServicePersonnel,
    OrgServicePolicy,
)

# 9. Execution projects, stages, sub-projects (FK → organisations + org_branches)
from models.org_project import (                                   # noqa: F401
    OrgProject,
    OrgProjectInCharge,
    OrgProjectStage,
    OrgProjectStageInCharge,
    OrgSubProject,
    OrgSubProjectInCharge,
)

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_MAX_RETRIES:   int = 5
_INITIAL_DELAY: int = 2   # seconds; doubles on each retry


# ─────────────────────────────────────────────────────────────────────────────
# init_db
# ─────────────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Orchestrate database setup with retry logic.

    1. Create all tables (idempotent — skips existing tables).
    2. Seed the initial super-admin user and platform roles.

    Raises RuntimeError if the database is unreachable after all retries,
    which aborts the FastAPI lifespan and prevents the service from starting.
    """
    delay = _INITIAL_DELAY

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log.info(
                "db.init.attempt",
                attempt=attempt,
                max=_MAX_RETRIES,
            )

            # ── 1. Create tables ──────────────────────────────────────────────
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("db.tables_ready : tables created")

            # ── 2. Seed initial data ──────────────────────────────────────────
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    # All seed writes are flushed inside seed_initial_data().
                    # db.begin() commits on exit or rolls back on exception.
                    await seed_initial_data(db)
            log.info("db.seed_complete")

            return   # ← success; exit the retry loop

        except SQLAlchemyError as exc:
            if attempt == _MAX_RETRIES:
                log.error(
                    "db.init.failed",
                    attempt=attempt,
                    error=str(exc),
                )
                raise RuntimeError(
                    "Application startup aborted: database unreachable "
                    f"after {_MAX_RETRIES} attempts."
                ) from exc

            log.warning(
                "db.init.retry",
                attempt=attempt,
                max=_MAX_RETRIES,
                retry_in_seconds=delay,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            await asyncio.sleep(delay)
            delay *= 2   # exponential back-off

        except Exception as exc:
            # Unexpected error (e.g. coding bug in seed) — fail fast, no retry.
            log.exception("db.init.unexpected_error", error=str(exc))
            raise RuntimeError(
                "Unexpected error during database initialisation."
            ) from exc
