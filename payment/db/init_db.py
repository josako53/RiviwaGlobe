"""db/init_db.py — payment_service"""
from __future__ import annotations
import asyncio
import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from db.session import engine
from models.payment import Payment, PaymentTransaction, WebhookLog  # noqa

log = structlog.get_logger(__name__)


async def init_db(max_retries: int = 5, initial_delay: float = 2.0) -> None:
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("payment.db.tables_created")
            return
        except (SQLAlchemyError, OSError) as exc:
            log.warning("payment.db.init.retry", attempt=attempt, error=str(exc))
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
    raise RuntimeError("payment_service: database unreachable")
