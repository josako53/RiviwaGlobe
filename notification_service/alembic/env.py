"""alembic/env.py — notification_service migration environment."""
from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel

# ── Import ALL models so SQLModel.metadata sees every table ──────────────────
# If a model is not imported here, Alembic will not detect it in autogenerate
# and the table will be missing from the generated migration.
from models.notification import (           # noqa: F401
    NotificationTemplate,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationDevice,
)

from core.config import settings

# ── Override sqlalchemy.url from environment settings ────────────────────────
# This ensures the correct host/port/credentials are used regardless of what
# is written in the [alembic] section of alembic.ini.
config = context.config
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


# ── Offline migrations (generate SQL without connecting) ─────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Used for generating SQL scripts to review before applying to production.

    Run with:
        alembic upgrade head --sql > migration.sql
    """
    context.configure(
        url              = config.get_main_option("sqlalchemy.url"),
        target_metadata  = target_metadata,
        literal_binds    = True,
        dialect_opts     = {"paramstyle": "named"},
        compare_type     = True,
        compare_server_default = True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations (connect and run directly) ─────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    This is the standard path used by `alembic upgrade head`.
    Uses psycopg (sync) driver — not asyncpg — because Alembic is synchronous.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix       = "sqlalchemy.",
        poolclass    = pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection             = connection,
            target_metadata        = target_metadata,
            compare_type           = True,
            compare_server_default = True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
