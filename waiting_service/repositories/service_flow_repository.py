from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ServiceFlowNotFoundError
from models.service_flow import FlowStep, ServiceFlow
from models.service_point import ServicePoint

log = structlog.get_logger(__name__)


class ServiceFlowRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, flow_data: dict, steps_data: List[dict]) -> ServiceFlow:
        flow = ServiceFlow(**flow_data)
        self.db.add(flow)
        await self.db.flush()
        for step_dict in steps_data:
            self.db.add(FlowStep(flow_id=flow.id, **step_dict))
        await self.db.flush()
        await self.db.refresh(flow)
        return flow

    async def get_by_id(self, flow_id: uuid.UUID) -> Optional[ServiceFlow]:
        result = await self.db.execute(select(ServiceFlow).where(ServiceFlow.id == flow_id))
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, flow_id: uuid.UUID) -> ServiceFlow:
        flow = await self.get_by_id(flow_id)
        if flow is None:
            raise ServiceFlowNotFoundError(f"Service flow {flow_id} not found.")
        return flow

    async def get_with_steps(self, flow_id: uuid.UUID) -> ServiceFlow:
        result = await self.db.execute(
            select(ServiceFlow).where(ServiceFlow.id == flow_id)
            .options(selectinload(ServiceFlow.steps).selectinload(FlowStep.service_point))
        )
        flow = result.scalar_one_or_none()
        if flow is None:
            raise ServiceFlowNotFoundError(f"Service flow {flow_id} not found.")
        return flow

    async def list_by_org(self, org_id: uuid.UUID, active_only: bool = True) -> List[ServiceFlow]:
        q = (select(ServiceFlow).where(ServiceFlow.org_id == org_id)
             .options(selectinload(ServiceFlow.steps).selectinload(FlowStep.service_point)))
        if active_only:
            q = q.where(ServiceFlow.is_active == True)  # noqa: E712
        result = await self.db.execute(q.order_by(ServiceFlow.is_default.desc(), ServiceFlow.name))
        return list(result.scalars().all())

    async def update(self, flow: ServiceFlow, data: dict) -> ServiceFlow:
        for k, v in data.items():
            setattr(flow, k, v)
        self.db.add(flow)
        await self.db.flush()
        await self.db.refresh(flow)
        return flow

    async def replace_steps(self, flow_id: uuid.UUID, steps_data: List[dict]) -> List[FlowStep]:
        await self.db.execute(delete(FlowStep).where(FlowStep.flow_id == flow_id))
        await self.db.flush()
        new_steps = []
        for step_dict in steps_data:
            step = FlowStep(flow_id=flow_id, **step_dict)
            self.db.add(step)
            new_steps.append(step)
        await self.db.flush()
        return new_steps

    async def get_step_by_order(self, flow_id: uuid.UUID, step_order: int) -> Optional[FlowStep]:
        result = await self.db.execute(
            select(FlowStep).where(FlowStep.flow_id == flow_id, FlowStep.step_order == step_order)
        )
        return result.scalar_one_or_none()

    async def get_next_step(self, flow_id: uuid.UUID, current_step_order: int) -> Optional[FlowStep]:
        return await self.get_step_by_order(flow_id, current_step_order + 1)

    async def get_entry_point(self, flow_id: uuid.UUID) -> Optional[ServicePoint]:
        result = await self.db.execute(
            select(FlowStep).where(FlowStep.flow_id == flow_id, FlowStep.step_order == 1)
            .options(selectinload(FlowStep.service_point))
        )
        step = result.scalar_one_or_none()
        return step.service_point if step else None
