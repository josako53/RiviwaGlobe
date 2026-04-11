"""db/init_db.py — ai_service"""
from __future__ import annotations
import asyncio
import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from db.session import engine
from models.conversation import AIConversation, ProjectKnowledgeBase, StakeholderCache  # noqa: F401

log = structlog.get_logger(__name__)


async def init_db(max_retries: int = 5, initial_delay: float = 2.0, backoff_factor: float = 2.0) -> None:
    delay    = initial_delay
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("ai.db.tables_created")
            return
        except (SQLAlchemyError, OSError) as exc:
            last_exc = exc
            log.warning("ai.db.init.retry", attempt=attempt, delay=delay, error=str(exc))
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor
    raise RuntimeError(f"ai_service: database unreachable after {max_retries} attempts.") from last_exc
