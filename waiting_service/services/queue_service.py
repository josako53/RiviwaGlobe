from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import TokenClaims
from core.exceptions import (
    CounterAlreadyBusyError, ForbiddenError, NoTicketsWaitingError,
    OrgNotFoundError, ServiceFlowNotFoundError, TicketNotWaitingError,
)
from events.producer import WaitingProducer
from models.org_cache import OrgCache
from models.queue_ticket import QueueTicket, TicketChannel, TicketPriority, TicketStatus
from models.queue_ticket_stage import QueueTicketStage, StageStatus
from waiting_redis.client import WaitingRedis
from repositories.queue_ticket_repository import QueueTicketRepository
from repositories.queue_ticket_stage_repository import QueueTicketStageRepository
from repositories.service_flow_repository import ServiceFlowRepository
from repositories.service_point_repository import ServicePointRepository
from repositories.staff_counter_repository import StaffCounterRepository
from repositories.staff_session_repository import StaffSessionRepository
from schemas.queue_ticket import FinishOut, TicketStatusOut
from schemas.service_point import ServicePointOut

log = structlog.get_logger(__name__)

_PRIORITY_MAP = {"NORMAL": TicketPriority.NORMAL, "HIGH": TicketPriority.HIGH, "URGENT": TicketPriority.URGENT}
_PRIORITY_STR = {TicketPriority.NORMAL: "NORMAL", TicketPriority.HIGH: "HIGH", TicketPriority.URGENT: "URGENT"}


@dataclass
class FinishResult:
    ticket:     QueueTicket
    is_final:   bool
    next_point: object = None


class QueueService:

    def __init__(self, db: AsyncSession, redis: WaitingRedis, producer: WaitingProducer) -> None:
        self.db        = db
        self.redis     = redis
        self.producer  = producer
        self.ticket_repo  = QueueTicketRepository(db)
        self.stage_repo   = QueueTicketStageRepository(db)
        self.flow_repo    = ServiceFlowRepository(db)
        self.point_repo   = ServicePointRepository(db)
        self.counter_repo = StaffCounterRepository(db)
        self.session_repo = StaffSessionRepository(db)

    async def _get_org_or_404(self, org_id: uuid.UUID) -> OrgCache:
        result = await self.db.execute(
            select(OrgCache).where(OrgCache.org_id == org_id, OrgCache.is_active == True)  # noqa: E712
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise OrgNotFoundError(f"Organisation {org_id} not found.")
        return org

    async def join_queue(self, data, token: Optional[TokenClaims]) -> QueueTicket:
        from schemas.queue_ticket import JoinQueueIn
        org = await self._get_org_or_404(data.org_id)
        flow = await self.flow_repo.get_by_id_or_404(data.flow_id)
        entry_point = await self.flow_repo.get_entry_point(data.flow_id)
        if entry_point is None:
            raise ServiceFlowNotFoundError("Service flow has no steps defined.")

        priority_int = _PRIORITY_MAP.get(str(data.priority).upper(), TicketPriority.NORMAL)
        channel = str(data.channel).upper() if hasattr(data, "channel") else TicketChannel.KIOSK

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        org_code = (org.slug or org.name[:8].replace(" ", "")).upper()

        ticket_number = await self.ticket_repo.next_ticket_sequence(data.org_id, org_code, date_str)

        ticket = await self.ticket_repo.create({
            "org_id":                   data.org_id,
            "ticket_number":            ticket_number,
            "external_id":              getattr(data, "external_id", None),
            "phone_number":             getattr(data, "phone_number", None),
            "submitter_name":           getattr(data, "submitter_name", None),
            "flow_id":                  data.flow_id,
            "current_service_point_id": entry_point.id,
            "current_step_order":       1,
            "status":                   TicketStatus.WAITING,
            "priority":                 priority_int,
            "channel":                  channel,
            "notes":                    getattr(data, "notes", None),
            "created_at":               now,
        })

        await self.stage_repo.create({
            "ticket_id":        ticket.id,
            "service_point_id": entry_point.id,
            "step_order":       1,
            "status":           StageStatus.WAITING,
            "entered_queue_at": now,
        })

        await self.redis.zadd_ticket(entry_point.id, ticket.id, _PRIORITY_STR[priority_int], now)
        position = (await self.redis.zrank_ticket(entry_point.id, ticket.id) or 0) + 1

        await self.producer.ticket_joined(
            ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket_number,
            flow_id=flow.id, channel=channel, priority=priority_int,
            service_point_name=entry_point.name, position=position,
            phone_number=ticket.phone_number,
        )
        log.info("waiting.ticket.joined", ticket_number=ticket_number, position=position)
        return ticket

    async def _resolve_counter(
        self,
        service_point_id: uuid.UUID,
        staff_counter_id: Optional[uuid.UUID],
        token: TokenClaims,
    ):
        """
        Resolve which StaffCounter to use for a call-next operation.

        Priority order:
          1. Explicit staff_counter_id provided — validate it directly.
          2. Staff has an active session at this service point — use that counter.
          3. Any available (idle) counter at the service point — auto-assign.
        """
        from core.exceptions import StaffCounterNotFoundError

        if staff_counter_id is not None:
            counter = await self.counter_repo.get_by_id_or_404(staff_counter_id)
            if token.org_id and counter.org_id != token.org_id:
                raise ForbiddenError()
            if not counter.is_available:
                raise CounterAlreadyBusyError()
            return counter

        # Try the staff member's active session at this service point
        session = await self.session_repo.get_active_for_staff(token.sub)
        if session and session.service_point_id == service_point_id:
            counter = await self.counter_repo.get_by_id_or_404(session.staff_counter_id)
            if counter.is_available:
                return counter
            raise CounterAlreadyBusyError(
                "Your assigned counter is already serving a ticket."
            )

        # Fall back to any idle counter at this service point
        available = await self.counter_repo.list_available_for_point(service_point_id)
        if not available:
            raise StaffCounterNotFoundError(
                "No available counters at this service point. Open a staff session first."
            )
        return available[0]

    async def call_next(
        self,
        service_point_id: uuid.UUID,
        staff_counter_id: Optional[uuid.UUID],
        token: TokenClaims,
    ) -> Tuple[QueueTicket, QueueTicketStage]:
        counter = await self._resolve_counter(service_point_id, staff_counter_id, token)
        staff_counter_id = counter.id

        ticket = await self.ticket_repo.get_next_waiting(service_point_id)
        if ticket is None:
            raise NoTicketsWaitingError()

        now = datetime.now(timezone.utc)
        await self.counter_repo.assign_ticket(staff_counter_id, ticket.id)
        ticket = await self.ticket_repo.update_status(ticket.id, TicketStatus.ATTENDING)

        stage = await self.stage_repo.get_active_stage(ticket.id)
        if stage:
            wait_secs = (now - stage.entered_queue_at).total_seconds()
            stage = await self.stage_repo.update(stage, {
                "status":               StageStatus.ATTENDING,
                "staff_counter_id":     staff_counter_id,
                "assigned_staff_user_id": token.sub,
                "attending_started_at": now,
                "wait_duration_seconds": wait_secs,
            })

        await self.redis.zrem_ticket(service_point_id, ticket.id)
        await self.redis.del_eta(ticket.id)

        await self.producer.ticket_attending(
            ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
            staff_counter_id=staff_counter_id, service_point_id=service_point_id,
            staff_user_id=token.sub,
        )
        return ticket, stage

    async def finish(
        self,
        ticket_id: uuid.UUID,
        staff_counter_id: Optional[uuid.UUID],
        notes: Optional[str],
        token: TokenClaims,
    ) -> FinishResult:
        ticket = await self.ticket_repo.get_by_id_or_404(ticket_id)
        if token.org_id and ticket.org_id != token.org_id:
            raise ForbiddenError()
        if ticket.status != TicketStatus.ATTENDING:
            raise TicketNotWaitingError("Ticket is not currently being attended.")

        # Auto-resolve counter: look up whichever counter currently holds this ticket
        if staff_counter_id is None:
            serving_counter = await self.counter_repo.get_counter_serving_ticket(ticket_id)
            if serving_counter is None:
                from core.exceptions import StaffCounterNotFoundError
                raise StaffCounterNotFoundError("No counter is currently assigned to this ticket.")
            staff_counter_id = serving_counter.id

        now = datetime.now(timezone.utc)
        stage = await self.stage_repo.get_active_stage(ticket_id)
        service_secs = 0.0
        if stage and stage.attending_started_at:
            service_secs = (now - stage.attending_started_at).total_seconds()
            await self.stage_repo.update(stage, {
                "status":                   StageStatus.FINISHED,
                "finished_at":              now,
                "service_duration_seconds": service_secs,
                "notes_by_staff":           notes,
            })

        await self.counter_repo.release_ticket(staff_counter_id)

        # Update staff session stats
        session = await self.session_repo.get_active_for_counter(staff_counter_id)
        if session:
            await self.session_repo.update_stats(session, service_secs)

        # Check for next flow step
        next_step = await self.flow_repo.get_next_step(ticket.flow_id, ticket.current_step_order)

        if next_step:
            next_point = await self.point_repo.get_by_id(next_step.service_point_id)
            ticket = await self.ticket_repo.update(ticket, {
                "status":                   TicketStatus.WAITING,
                "current_service_point_id": next_step.service_point_id,
                "current_step_order":       next_step.step_order,
            })
            await self.stage_repo.create({
                "ticket_id":        ticket.id,
                "service_point_id": next_step.service_point_id,
                "step_order":       next_step.step_order,
                "status":           StageStatus.WAITING,
                "entered_queue_at": now,
            })
            await self.redis.zadd_ticket(
                next_step.service_point_id, ticket.id,
                _PRIORITY_STR[ticket.priority], now,
            )
            await self.producer.ticket_finished(
                ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
                service_point_id=stage.service_point_id if stage else next_step.service_point_id,
                wait_secs=stage.wait_duration_seconds if stage else None,
                service_secs=service_secs, is_final=False,
            )
            await self.producer.ticket_stage_advanced(
                ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
                next_point_name=next_point.name if next_point else "next stage",
                current_step_order=next_step.step_order,
            )
            return FinishResult(ticket=ticket, is_final=False, next_point=next_point)
        else:
            ticket = await self.ticket_repo.update_status(
                ticket.id, TicketStatus.COMPLETED, completed_at=now
            )
            await self.producer.ticket_finished(
                ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
                service_point_id=stage.service_point_id if stage else ticket.current_service_point_id,
                wait_secs=stage.wait_duration_seconds if stage else None,
                service_secs=service_secs, is_final=True,
            )
            await self.producer.ticket_completed(
                ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number
            )
            return FinishResult(ticket=ticket, is_final=True)

    async def cancel_ticket(self, ticket_id: uuid.UUID, token: TokenClaims) -> QueueTicket:
        ticket = await self.ticket_repo.get_by_id_or_404(ticket_id)
        if token.org_id and ticket.org_id != token.org_id:
            raise ForbiddenError()
        ticket = await self.ticket_repo.update_status(ticket.id, TicketStatus.CANCELLED)
        await self.redis.zrem_ticket(ticket.current_service_point_id, ticket.id)
        await self.redis.del_eta(ticket.id)
        await self.producer.ticket_cancelled(
            ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number
        )
        return ticket

    async def mark_no_show(
        self, ticket_id: uuid.UUID, staff_counter_id: uuid.UUID, token: TokenClaims
    ) -> QueueTicket:
        ticket = await self.ticket_repo.get_by_id_or_404(ticket_id)
        if token.org_id and ticket.org_id != token.org_id:
            raise ForbiddenError()
        ticket = await self.ticket_repo.update_status(ticket.id, TicketStatus.NO_SHOW)
        await self.counter_repo.release_ticket(staff_counter_id)
        await self.redis.zrem_ticket(ticket.current_service_point_id, ticket.id)
        return ticket

    async def get_ticket_status(self, ticket_id: uuid.UUID) -> QueueTicket:
        return await self.ticket_repo.get_by_id_or_404(ticket_id)

    async def set_priority(
        self, ticket_id: uuid.UUID, priority: str, reason: Optional[str], token: TokenClaims
    ) -> QueueTicket:
        ticket = await self.ticket_repo.get_by_id_or_404(ticket_id)
        if token.org_id and ticket.org_id != token.org_id:
            raise ForbiddenError()
        if ticket.status != TicketStatus.WAITING:
            raise TicketNotWaitingError("Can only change priority of a WAITING ticket.")
        old_priority = ticket.priority
        new_priority_int = _PRIORITY_MAP.get(priority.upper(), TicketPriority.NORMAL)
        ticket = await self.ticket_repo.update(ticket, {"priority": new_priority_int})
        # Re-score in Redis
        await self.redis.zrem_ticket(ticket.current_service_point_id, ticket.id)
        await self.redis.zadd_ticket(
            ticket.current_service_point_id, ticket.id,
            priority.upper(), ticket.created_at,
        )
        await self.producer.ticket_priority_changed(
            ticket_id=ticket.id, org_id=ticket.org_id, ticket_number=ticket.ticket_number,
            old_priority=old_priority, new_priority=new_priority_int,
            phone_number=ticket.phone_number, reason=reason,
        )
        return ticket

    async def enrich_with_live_data(self, ticket: QueueTicket) -> dict:
        """Overlay Redis position + ETA onto ticket for status responses."""
        data = {
            "id": ticket.id, "ticket_number": ticket.ticket_number,
            "org_id": ticket.org_id, "flow_id": ticket.flow_id,
            "current_service_point_id": ticket.current_service_point_id,
            "current_step_order": ticket.current_step_order,
            "status": ticket.status, "priority": ticket.priority,
            "channel": ticket.channel, "created_at": ticket.created_at,
            "completed_at": ticket.completed_at, "notes": ticket.notes,
            "phone_number": ticket.phone_number, "submitter_name": ticket.submitter_name,
        }
        if ticket.status == TicketStatus.WAITING:
            rank = await self.redis.zrank_ticket(ticket.current_service_point_id, ticket.id)
            data["position_in_queue"] = (rank + 1) if rank is not None else None
            data["eta_minutes"] = await self.redis.get_eta(ticket.id)
        else:
            data["position_in_queue"] = None
            data["eta_minutes"] = None
        stage = await self.stage_repo.get_active_stage(ticket.id)
        data["current_stage"] = stage
        return data
