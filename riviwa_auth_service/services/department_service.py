"""
services/department_service.py
─────────────────────────────────────────────────────────────────────────────
Business logic for OrgDepartment CRUD.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DepartmentNameConflictError, DepartmentNotFoundError
from events.publisher import EventPublisher
from models.department import OrgDepartment


class DepartmentService:

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db        = db
        self.publisher = publisher

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_or_404(self, dept_id: uuid.UUID, org_id: uuid.UUID) -> OrgDepartment:
        result = await self.db.execute(
            select(OrgDepartment).where(
                OrgDepartment.id == dept_id,
                OrgDepartment.org_id == org_id,
            )
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise DepartmentNotFoundError()
        return dept

    async def _check_name_unique(
        self, org_id: uuid.UUID, name: str, exclude_id: Optional[uuid.UUID] = None
    ) -> None:
        q = select(OrgDepartment).where(
            OrgDepartment.org_id == org_id,
            OrgDepartment.name == name,
        )
        if exclude_id:
            q = q.where(OrgDepartment.id != exclude_id)
        result = await self.db.execute(q)
        if result.scalar_one_or_none():
            raise DepartmentNameConflictError()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(self, org_id: uuid.UUID, data: dict, created_by: uuid.UUID) -> OrgDepartment:
        await self._check_name_unique(org_id, data["name"])

        dept = OrgDepartment(
            org_id        = org_id,
            branch_id     = data.get("branch_id"),
            name          = data["name"],
            code          = data.get("code"),
            description   = data.get("description"),
            sort_order    = data.get("sort_order", 0),
            created_by_id = created_by,
        )
        self.db.add(dept)
        await self.db.commit()
        await self.db.refresh(dept)
        await self.publisher.org_department_created(dept)
        return dept

    async def list(
        self,
        org_id:      uuid.UUID,
        branch_id:   Optional[uuid.UUID] = None,
        active_only: bool = True,
    ) -> list[OrgDepartment]:
        q = select(OrgDepartment).where(OrgDepartment.org_id == org_id)
        if active_only:
            q = q.where(OrgDepartment.is_active == True)  # noqa: E712
        if branch_id is not None:
            # Return departments scoped to this branch OR org-wide ones
            q = q.where(
                (OrgDepartment.branch_id == branch_id) |
                (OrgDepartment.branch_id == None)  # noqa: E711
            )
        q = q.order_by(OrgDepartment.sort_order, OrgDepartment.name)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get(self, dept_id: uuid.UUID, org_id: uuid.UUID) -> OrgDepartment:
        return await self._get_or_404(dept_id, org_id)

    async def update(
        self, dept_id: uuid.UUID, org_id: uuid.UUID, data: dict
    ) -> OrgDepartment:
        dept = await self._get_or_404(dept_id, org_id)
        changed: list[str] = []

        if "name" in data and data["name"] and data["name"] != dept.name:
            await self._check_name_unique(org_id, data["name"], exclude_id=dept_id)
            dept.name = data["name"]
            changed.append("name")

        for field in ("code", "description", "branch_id", "sort_order", "is_active"):
            if field in data and data[field] is not None:
                if getattr(dept, field) != data[field]:
                    setattr(dept, field, data[field])
                    changed.append(field)

        if changed:
            await self.db.commit()
            await self.db.refresh(dept)
            await self.publisher.org_department_updated(dept, changed)
        return dept

    async def deactivate(self, dept_id: uuid.UUID, org_id: uuid.UUID) -> OrgDepartment:
        dept = await self._get_or_404(dept_id, org_id)
        dept.is_active = False
        await self.db.commit()
        await self.db.refresh(dept)
        await self.publisher.org_department_deactivated(dept)
        return dept
