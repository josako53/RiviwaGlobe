from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UrgencyRequestNotFoundError
from models.urgency_request import UrgencyRequest, UrgencyStatus

log = structlog.get_logger(__name__)


class UrgencyRequestRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> UrgencyRequest:
        request = UrgencyRequest(**data)
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_by_id(self, request_id: uuid.UUID) -> Optional[UrgencyRequest]:
        result = await self.db.execute(
            select(UrgencyRequest).where(UrgencyRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, request_id: uuid.UUID) -> UrgencyRequest:
        request = await self.get_by_id(request_id)
        if request is None:
            raise UrgencyRequestNotFoundError(f"Urgency request {request_id} not found.")
        return request

    async def get_pending_for_ticket(self, ticket_id: uuid.UUID) -> Optional[UrgencyRequest]:
        result = await self.db.execute(
            select(UrgencyRequest).where(
                UrgencyRequest.ticket_id == ticket_id,
                UrgencyRequest.status == UrgencyStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_by_org(self, org_id: uuid.UUID, skip: int, limit: int) -> List[UrgencyRequest]:
        result = await self.db.execute(
            select(UrgencyRequest).where(
                UrgencyRequest.org_id == org_id,
                UrgencyRequest.status == UrgencyStatus.PENDING,
            ).order_by(UrgencyRequest.requested_at.asc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def review(
        self,
        request: UrgencyRequest,
        status: str,
        reviewed_by: uuid.UUID,
        notes: Optional[str],
    ) -> UrgencyRequest:
        request.status = status
        request.reviewed_by_user_id = reviewed_by
        request.reviewed_at = datetime.now(timezone.utc)
        if notes is not None:
            request.reviewer_notes = notes
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request
