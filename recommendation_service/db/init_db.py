"""db/init_db.py — Create tables and PostGIS extension."""
from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import text
from sqlmodel import SQLModel

from db.session import engine

log = structlog.get_logger(__name__)

# Import all models so SQLModel.metadata knows every table
from models.entity import RecommendationEntity, ActivityEvent  # noqa: F401


async def init_db(max_retries: int = 5, delay: float = 3.0) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            log.info("db.init.attempt", attempt=attempt, max=max_retries)
            async with engine.begin() as conn:
                # Enable PostGIS extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("db.tables_ready")
            return
        except Exception as exc:
            log.warning("db.init.retry", attempt=attempt, error=str(exc))
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay * attempt)
