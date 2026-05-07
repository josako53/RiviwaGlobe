from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import TokenClaims
from core.exceptions import ForbiddenError, SessionAlreadyOpenError, StaffSessionNotFoundError
from events.producer import WaitingProducer
from repositories.staff_counter_repository import StaffCounterRepository
from repositories.staff_session_repository import StaffSessionRepository
from schemas.staff_counter import SessionOut

log = structlog.get_logger(__name__)


class StaffSessionService:

    def __init__(self, db: AsyncSession, producer: WaitingProducer) -> None:
        self.db           = db
        self.producer     = producer
        self.counter_repo = StaffCounterRepository(db)
        self.session_repo = StaffSessionRepository(db)

    async def open_session(self, data, token: TokenClaims) -> SessionOut:
        counter_id = data.staff_counter_id
        counter = await self.counter_repo.get_by_id_or_404(counter_id)
        if token.org_id and counter.org_id != token.org_id:
            raise ForbiddenError()
        existing = await self.session_repo.get_active_for_counter(counter_id)
        if existing:
            raise SessionAlreadyOpenError()

        session = await self.session_repo.create({
            "org_id":            counter.org_id,
            "staff_user_id":     token.sub,
            "staff_counter_id":  counter_id,
            "service_point_id":  counter.service_point_id,
            "opened_at":         datetime.now(timezone.utc),
            "is_active":         True,
            "tickets_served":    0,
            "avg_service_seconds": 0.0,
        })
        await self.producer.staff_session_opened(
            session_id=session.id, org_id=session.org_id,
            counter_id=counter_id, service_point_id=counter.service_point_id,
            staff_user_id=token.sub,
        )
        log.info("waiting.session.opened", counter_id=str(counter_id), user=str(token.sub))
        return SessionOut.model_validate(session)

    async def close_session(self, counter_id: uuid.UUID, token: TokenClaims) -> SessionOut:
        counter = await self.counter_repo.get_by_id_or_404(counter_id)
        if token.org_id and counter.org_id != token.org_id:
            raise ForbiddenError()
        session = await self.session_repo.get_active_for_counter(counter_id)
        if session is None:
            raise StaffSessionNotFoundError("No active session found for this counter.")
        closed = await self.session_repo.close(session, datetime.now(timezone.utc))
        # Release counter if it still has a current_ticket_id
        if counter.current_ticket_id:
            await self.counter_repo.release_ticket(counter_id)
        await self.producer.staff_session_closed(
            session_id=closed.id, org_id=closed.org_id,
            tickets_served=closed.tickets_served,
            avg_service_seconds=closed.avg_service_seconds,
        )
        log.info("waiting.session.closed", counter_id=str(counter_id), served=closed.tickets_served)
        return SessionOut.model_validate(closed)

    async def get_active_session(self, counter_id: uuid.UUID, token: TokenClaims):
        counter = await self.counter_repo.get_by_id_or_404(counter_id)
        if token.org_id and counter.org_id != token.org_id:
            raise ForbiddenError()
        return await self.session_repo.get_active_for_counter(counter_id)
