"""
services/project_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for the project cache read endpoints.
Projects are synced read-only from auth_service — no mutations here.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ProjectNotFoundError
from models.project import ProjectCache, ProjectStatus
from repositories.project_repository import ProjectRepository


class ProjectService:

    def __init__(self, db: AsyncSession) -> None:
        self.repo = ProjectRepository(db)

    async def list(
        self,
        status: Optional[ProjectStatus] = None,
        org_id: Optional[uuid.UUID]     = None,
        lga:    Optional[str]           = None,
        skip:   int                     = 0,
        limit:  int                     = 50,
    ) -> list[ProjectCache]:
        return await self.repo.list(status=status, org_id=org_id, lga=lga, skip=skip, limit=limit)

    async def get_or_404(self, project_id: uuid.UUID) -> ProjectCache:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError()
        return project

    async def get_with_counts(self, project_id: uuid.UUID) -> tuple[ProjectCache, dict]:
        project = await self.repo.get_by_id_with_stages(project_id)
        if not project:
            raise ProjectNotFoundError()
        counts = await self.repo.engagement_counts(project_id)
        return project, counts
