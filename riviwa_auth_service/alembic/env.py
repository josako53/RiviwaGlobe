"""
alembic/env.py
═══════════════════════════════════════════════════════════════════════════════
Alembic environment configuration for the Riviwa Auth Service.

Connection URL
───────────────
  Reads settings.SYNC_DATABASE_URL at runtime so credentials are always
  sourced from environment variables — never from alembic.ini.

  URL uses the psycopg v3 driver (postgresql+psycopg) for sync operations.
  The async app uses asyncpg; Alembic uses psycopg because Alembic's
  migration runner is synchronous.

  Ensure psycopg[binary] is in requirements.txt:
      psycopg[binary]>=3.1

Target metadata
────────────────
  Imports all model classes via db/base.py so SQLModel.metadata contains
  all 27 table definitions before autogenerate runs. Any model NOT imported
  in base.py will cause Alembic to generate a DROP TABLE migration for it.

Usage
──────
  # Apply all pending migrations (production)
  alembic upgrade head

  # Generate new migration after model change
  alembic revision --autogenerate -m "add_column_users_last_seen"

  # Roll back one revision
  alembic downgrade -1

  # Show current state
  alembic current
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import sys
import os

# ── Ensure app modules are importable from the project root ──────────────────
# alembic.ini sets prepend_sys_path = . which adds the project root to
# sys.path.  This explicit insert is a safety net for IDE / CI environments
# where alembic is invoked from a different working directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Load all models into SQLModel.metadata via db/base.py ────────────────────
# This single import triggers every model import in dependency order.
# DO NOT skip this — missing it means Alembic cannot see those tables.
from db.base import Base   # noqa: F401  (side-effect import — registers all models)

# ── App settings — provides SYNC_DATABASE_URL ─────────────────────────────────
from core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Alembic Config object (provides .ini values, including logging setup)
# ─────────────────────────────────────────────────────────────────────────────

config = context.config

# Apply the logging configuration from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Override the connection URL with the runtime value ────────────────────────
# This is the key line: credentials from environment variables, not from
# the hardcoded fallback in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

# ── Target metadata — tells autogenerate which tables should exist ────────────
target_metadata = Base.metadata


# ─────────────────────────────────────────────────────────────────────────────
# Offline migration (generates SQL without a live DB connection)
# ─────────────────────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL string (no Engine connection).
    Generates a SQL script that can be applied manually — useful for:
      · Reviewing exactly what SQL will run before applying it.
      · Environments where the migration runner does not have DB access
        (e.g. CI pipeline generates SQL, ops team applies it).

    Usage:  alembic upgrade head --sql > migrations.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas so cross-schema FK references are tracked
        include_schemas=True,
        # Compare server defaults so Alembic detects column default changes
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
# Online migration (applies changes to a live DB connection)
# ─────────────────────────────────────────────────────────────────────────────

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (the default for `alembic upgrade`).

    Creates an Engine and opens a Connection, then runs all pending
    migration scripts against the live database.

    NullPool is used so that Alembic does not hold open connections after
    the migration completes. This is safe for one-shot migration runs and
    avoids connection leaks in CI pipelines.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect changes to server_default values
            compare_server_default=True,
            # Include all schemas in the comparison
            include_schemas=True,
            # Render AS IDENTITY instead of sequences for PG 10+
            # (SQLModel uses UUID primary keys so this is informational)
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
