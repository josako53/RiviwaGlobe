"""services/committee_service.py — GRM committee management"""
from __future__ import annotations
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import CommitteeNotFoundError
from models.feedback import CommitteeLevel, CommitteeRole, GrievanceCommittee
from repositories.committee_repository import CommitteeRepository


class CommitteeService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CommitteeRepository(db)
        self.db   = db

    async def create(self, data: dict) -> GrievanceCommittee:
        sids = data.get("stakeholder_ids")
        c = GrievanceCommittee(
            name               = data["name"],
            level              = CommitteeLevel(data["level"]),
            project_id         = uuid.UUID(data["project_id"])         if data.get("project_id")         else None,
            lga                = data.get("lga"),
            org_sub_project_id = uuid.UUID(data["org_sub_project_id"]) if data.get("org_sub_project_id") else None,
            stakeholder_ids    = {"stakeholder_ids": sids}             if sids                            else None,
            description        = data.get("description"),
        )
        c = await self.repo.create(c)
        await self.db.commit()
        return c

    async def get_or_404(self, committee_id: uuid.UUID) -> GrievanceCommittee:
        c = await self.repo.get_by_id(committee_id)
        if not c:
            raise CommitteeNotFoundError()
        return c

    async def list(self, **filters) -> list[GrievanceCommittee]:
        return await self.repo.list(**filters)

    async def update(self, committee_id: uuid.UUID, data: dict) -> GrievanceCommittee:
        c = await self.get_or_404(committee_id)
        for field in ("name", "lga", "description", "is_active"):
            if field in data:
                setattr(c, field, data[field])
        if "org_sub_project_id" in data:
            c.org_sub_project_id = uuid.UUID(data["org_sub_project_id"]) if data["org_sub_project_id"] else None
        if "stakeholder_ids" in data:
            ids = data["stakeholder_ids"]
            c.stakeholder_ids = {"stakeholder_ids": ids} if ids else None
        await self.repo.save(c)
        await self.db.commit()
        return c

    async def add_stakeholder(self, committee_id: uuid.UUID, stakeholder_id: uuid.UUID) -> GrievanceCommittee:
        c       = await self.get_or_404(committee_id)
        current = c.get_stakeholder_ids()
        sid     = str(stakeholder_id)
        if sid not in current:
            current.append(sid)
            c.stakeholder_ids = {"stakeholder_ids": current}
            await self.repo.save(c)
            await self.db.commit()
        return c

    async def remove_stakeholder(self, committee_id: uuid.UUID, stakeholder_id: uuid.UUID) -> GrievanceCommittee:
        c       = await self.get_or_404(committee_id)
        current = c.get_stakeholder_ids()
        sid     = str(stakeholder_id)
        if sid in current:
            current.remove(sid)
            c.stakeholder_ids = {"stakeholder_ids": current} if current else None
            await self.repo.save(c)
            await self.db.commit()
        return c

    async def add_member(self, committee_id: uuid.UUID, data: dict):
        await self.get_or_404(committee_id)
        m = await self.repo.create_member(
            committee_id = committee_id,
            user_id      = uuid.UUID(data["user_id"]),
            role         = CommitteeRole(data.get("role", "member")),
        )
        await self.db.commit()
        await self.db.refresh(m)
        return m

    async def remove_member(self, committee_id: uuid.UUID, user_id: uuid.UUID) -> None:
        m = await self.repo.get_active_member(committee_id, user_id)
        if not m:
            raise CommitteeNotFoundError()
        await self.repo.deactivate_member(m)
        await self.db.commit()
