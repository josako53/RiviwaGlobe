from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import TokenClaims
from core.exceptions import ForbiddenError, PriorityEscalationError, TicketNotWaitingError
from events.producer import WaitingProducer
from models.queue_ticket import TicketPriority, TicketStatus
from models.urgency_request import UrgencyStatus
from waiting_redis.client import WaitingRedis
from repositories.queue_ticket_repository import QueueTicketRepository
from repositories.urgency_request_repository import UrgencyRequestRepository
from schemas.urgency_request import UrgencyRequestIn, UrgencyRequestOut, UrgencyReviewIn

log = structlog.get_logger(__name__)

_PRIORITY_STR = {TicketPriority.NORMAL: "NORMAL", TicketPriority.HIGH: "HIGH", TicketPriority.URGENT: "URGENT"}


class UrgencyService:

    def __init__(self, db: AsyncSession, redis: WaitingRedis, producer: WaitingProducer) -> None:
        self.db        = db
        self.redis     = redis
        self.producer  = producer
        self.ticket_repo  = QueueTicketRepository(db)
        self.urgency_repo = UrgencyRequestRepository(db)

    async def submit_request(
        self, ticket_id: uuid.UUID, data: UrgencyRequestIn, token: Optional[TokenClaims]
    ) -> UrgencyRequestOut:
        ticket = await self.ticket_repo.get_by_id_or_404(ticket_id)
        if ticket.status != TicketStatus.WAITING:
            raise TicketNotWaitingError("Can only submit urgency request for a WAITING ticket.")
        existing = await self.urgency_repo.get_pending_for_ticket(ticket_id)
        if existing:
            raise PriorityEscalationError("A pending urgency request already exists for this ticket.")

        request = await self.urgency_repo.create({
            "ticket_id":            ticket_id,
            "org_id":               ticket.org_id,
            "requested_by_user_id": token.sub if token else None,
            "urgency_type":         data.urgency_type.upper(),
            "evidence_notes":       data.evidence_notes,
            "status":               UrgencyStatus.PENDING,
            "requested_at":         datetime.now(timezone.utc),
        })
        log.info("waiting.urgency.submitted", ticket_number=ticket.ticket_number, type=data.urgency_type)
        return UrgencyRequestOut.model_validate(request)

    async def review(
        self, request_id: uuid.UUID, data: UrgencyReviewIn, token: TokenClaims
    ) -> UrgencyRequestOut:
        request = await self.urgency_repo.get_by_id_or_404(request_id)
        if token.org_id and request.org_id != token.org_id:
            raise ForbiddenError()
        if request.status != UrgencyStatus.PENDING:
            raise PriorityEscalationError("This urgency request is not in PENDING state.")

        new_status = data.status.upper()
        request = await self.urgency_repo.review(request, new_status, token.sub, data.reviewer_notes)

        if new_status == UrgencyStatus.APPROVED:
            ticket = await self.ticket_repo.get_by_id_or_404(request.ticket_id)
            old_priority = ticket.priority
            if ticket.priority < TicketPriority.URGENT:
                ticket = await self.ticket_repo.update(ticket, {"priority": TicketPriority.URGENT})
                await self.redis.zrem_ticket(ticket.current_service_point_id, ticket.id)
                await self.redis.zadd_ticket(
                    ticket.current_service_point_id, ticket.id, "URGENT", ticket.created_at
                )
                await self.producer.ticket_priority_changed(
                    ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
                    old_priority=old_priority, new_priority=TicketPriority.URGENT,
                    phone_number=ticket.phone_number, reason=f"Urgency approved: {request.urgency_type}",
                )
            await self.producer.urgency_approved(
                ticket_id=ticket.id, request_id=request.id,
                org_id=request.org_id, urgency_type=request.urgency_type,
                new_priority=TicketPriority.URGENT,
            )
        else:
            ticket = await self.ticket_repo.get_by_id_or_404(request.ticket_id)
            await self.producer.urgency_rejected(
                ticket_id=ticket.id, request_id=request.id,
                org_id=request.org_id, reviewer_notes=data.reviewer_notes,
            )

        return UrgencyRequestOut.model_validate(request)

    async def list_pending(
        self, org_id: uuid.UUID, token: TokenClaims, skip: int, limit: int
    ) -> List[UrgencyRequestOut]:
        if token.org_id and token.org_id != org_id:
            raise ForbiddenError()
        requests = await self.urgency_repo.list_pending_by_org(org_id, skip, limit)
        return [UrgencyRequestOut.model_validate(r) for r in requests]
