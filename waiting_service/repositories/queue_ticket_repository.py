from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import TicketNotFoundError
from models.queue_ticket import QueueTicket, TicketPriority, TicketStatus

log = structlog.get_logger(__name__)


class QueueTicketRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_ticket_sequence(self, org_id: uuid.UUID, org_code: str, date_str: str) -> str:
        """Atomic per-org-per-day sequence. Returns ticket number like ORGCODE-20260507-0042."""
        from datetime import date as date_type
        date_obj = date_type.fromisoformat(date_str)
        result = await self.db.execute(
            text("""
                INSERT INTO waiting_ticket_sequences (org_id, date, last_value)
                VALUES (:org_id, :date, 1)
                ON CONFLICT (org_id, date)
                DO UPDATE SET last_value = waiting_ticket_sequences.last_value + 1
                RETURNING last_value
            """),
            {"org_id": str(org_id), "date": date_obj},
        )
        seq: int = result.scalar()
        return f"{org_code.upper()}-{date_str.replace('-', '')}-{seq:04d}"

    async def create(self, data: dict) -> QueueTicket:
        ticket = QueueTicket(**data)
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        log.info("waiting.ticket.created", ticket_number=ticket.ticket_number)
        return ticket

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[QueueTicket]:
        result = await self.db.execute(select(QueueTicket).where(QueueTicket.id == ticket_id))
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, ticket_id: uuid.UUID) -> QueueTicket:
        ticket = await self.get_by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found.")
        return ticket

    async def get_by_ticket_number(self, ticket_number: str) -> Optional[QueueTicket]:
        result = await self.db.execute(
            select(QueueTicket).where(QueueTicket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, org_id: uuid.UUID, external_id: str) -> Optional[QueueTicket]:
        result = await self.db.execute(
            select(QueueTicket).where(
                QueueTicket.org_id == org_id,
                QueueTicket.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_next_waiting(self, service_point_id: uuid.UUID) -> Optional[QueueTicket]:
        """Next ticket: highest priority (lowest int), then earliest created_at (FIFO)."""
        result = await self.db.execute(
            select(QueueTicket).where(
                QueueTicket.current_service_point_id == service_point_id,
                QueueTicket.status == TicketStatus.WAITING,
            ).order_by(QueueTicket.priority.asc(), QueueTicket.created_at.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_position_in_queue(self, ticket_id: uuid.UUID, service_point_id: uuid.UUID) -> int:
        ref = await self.get_by_id(ticket_id)
        if ref is None:
            return 0
        count = await self.db.scalar(
            select(func.count(QueueTicket.id)).where(
                QueueTicket.current_service_point_id == service_point_id,
                QueueTicket.status == TicketStatus.WAITING,
                (
                    (QueueTicket.priority < ref.priority) |
                    (
                        (QueueTicket.priority == ref.priority) &
                        (QueueTicket.created_at <= ref.created_at)
                    )
                ),
            )
        ) or 0
        return max(count, 1)

    async def get_tickets_in_queue(self, service_point_id: uuid.UUID) -> List[QueueTicket]:
        result = await self.db.execute(
            select(QueueTicket).where(
                QueueTicket.current_service_point_id == service_point_id,
                QueueTicket.status == TicketStatus.WAITING,
            ).order_by(QueueTicket.priority.asc(), QueueTicket.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_status(self, ticket_id: uuid.UUID, status: str, **extra_fields) -> QueueTicket:
        ticket = await self.get_by_id_or_404(ticket_id)
        ticket.status = status
        ticket.updated_at = datetime.now(timezone.utc)
        for k, v in extra_fields.items():
            setattr(ticket, k, v)
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def update(self, ticket: QueueTicket, data: dict) -> QueueTicket:
        data.setdefault("updated_at", datetime.now(timezone.utc))
        for k, v in data.items():
            setattr(ticket, k, v)
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def count_by_status_and_point(self, service_point_id: uuid.UUID, status: str) -> int:
        return await self.db.scalar(
            select(func.count(QueueTicket.id)).where(
                QueueTicket.current_service_point_id == service_point_id,
                QueueTicket.status == status,
            )
        ) or 0

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        status: Optional[str],
        service_point_id: Optional[uuid.UUID],
        skip: int,
        limit: int,
    ) -> Tuple[List[QueueTicket], int]:
        base = select(QueueTicket).where(QueueTicket.org_id == org_id)
        if status:
            base = base.where(QueueTicket.status == status)
        if service_point_id:
            base = base.where(QueueTicket.current_service_point_id == service_point_id)
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.execute(
            base.order_by(QueueTicket.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total
