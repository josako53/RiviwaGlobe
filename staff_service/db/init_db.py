from __future__ import annotations

import structlog
from sqlmodel import SQLModel

from db.session import engine

log = structlog.get_logger(__name__)


async def init_db() -> None:
    """Create all tables via SQLModel metadata (fallback if no alembic versions exist)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("staff_service.db_ready")
