"""
db/init_db.py - Database initialisation for stakeholder_service.
Table creation order follows FK dependencies.
"""
from __future__ import annotations
import asyncio
import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel

from db.session import AsyncSessionLocal, engine

# 1. Projects cache (no FK deps within this service)
from models.project import ProjectCache, ProjectStageCache              # noqa: F401

# 2. Stakeholders (no FK deps within this service)
from models.stakeholder import Stakeholder, StakeholderProject         # noqa: F401
from models.stakeholder import StakeholderContact                      # noqa: F401
from models.stakeholder import StakeholderStageEngagement              # noqa: F401

# 3. Engagement (FK → ProjectCache, StakeholderContact)
from models.engagement import EngagementActivity, StakeholderEngagement # noqa: F401

# 4. Communication (FK → ProjectCache, StakeholderContact)
from models.communication import (                                      # noqa: F401
    CommunicationRecord,
    CommunicationDistribution,
    FocalPerson,
)

log = structlog.get_logger(__name__)


async def init_db(max_retries: int = 5, initial_delay: float = 2.0, backoff_factor: float = 2.0) -> None:
    delay = initial_delay
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            log.info("stakeholder.db.init.attempt", attempt=attempt)
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("stakeholder.db.tables_created")
            return
        except (SQLAlchemyError, OSError, ConnectionRefusedError) as exc:
            last_exc = exc
            log.warning("stakeholder.db.init.retry", attempt=attempt, delay=delay, error=str(exc))
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor
    raise RuntimeError(f"stakeholder_service: database unreachable after {max_retries} attempts.") from last_exc
