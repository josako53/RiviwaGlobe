from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Import all models so SQLModel.metadata is fully populated
from models.org_cache import OrgCache                  # noqa: F401
from models.service_point import ServicePoint          # noqa: F401
from models.service_flow import ServiceFlow, FlowStep  # noqa: F401
from models.staff_counter import StaffCounter          # noqa: F401
from models.queue_ticket import QueueTicket            # noqa: F401
from models.queue_ticket_stage import QueueTicketStage # noqa: F401
from models.urgency_request import UrgencyRequest      # noqa: F401
from models.staff_session import StaffSession          # noqa: F401
from core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
