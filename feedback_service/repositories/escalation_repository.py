# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service  |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  repositories/escalation_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/escalation_repository.py
═══════════════════════════════════════════════════════════════════════════════
All DB operations for EscalationPath and EscalationLevel.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.escalation import EscalationLevel, EscalationPath

log = structlog.get_logger(__name__)


class EscalationRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Path reads ────────────────────────────────────────────────────────────

    async def get_path(self, path_id: uuid.UUID) -> Optional[EscalationPath]:
        """Get path without levels loaded."""
        result = await self.db.execute(
            select(EscalationPath).where(EscalationPath.id == path_id)
        )
        return result.scalar_one_or_none()

    async def get_path_with_levels(self, path_id: uuid.UUID) -> Optional[EscalationPath]:
        """Get path with all levels eagerly loaded, sorted by level_order."""
        result = await self.db.execute(
            select(EscalationPath)
            .where(EscalationPath.id == path_id)
            .options(selectinload(EscalationPath.levels))
        )
        return result.scalar_one_or_none()

    async def list_paths_for_org(
        self,
        org_id: uuid.UUID,
        active_only: bool = True,
    ) -> List[EscalationPath]:
        """List all paths for an org (including project-specific ones), with levels."""
        q = (
            select(EscalationPath)
            .where(EscalationPath.org_id == org_id)
            .options(selectinload(EscalationPath.levels))
            .order_by(EscalationPath.is_default.desc(), EscalationPath.created_at)
        )
        if active_only:
            q = q.where(EscalationPath.is_active == True)  # noqa: E712
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_org_default_path(self, org_id: uuid.UUID) -> Optional[EscalationPath]:
        """Return the org-wide default path with levels, or None if not set."""
        result = await self.db.execute(
            select(EscalationPath)
            .where(
                EscalationPath.org_id == org_id,
                EscalationPath.is_default == True,   # noqa: E712
                EscalationPath.is_active == True,    # noqa: E712
            )
            .options(selectinload(EscalationPath.levels))
        )
        return result.scalar_one_or_none()

    async def get_system_template(self) -> Optional[EscalationPath]:
        """Return the system-wide default template with levels."""
        result = await self.db.execute(
            select(EscalationPath)
            .where(
                EscalationPath.is_system_template == True,  # noqa: E712
                EscalationPath.is_active == True,           # noqa: E712
            )
            .options(selectinload(EscalationPath.levels))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_system_templates(self) -> List[EscalationPath]:
        result = await self.db.execute(
            select(EscalationPath)
            .where(EscalationPath.is_system_template == True)  # noqa: E712
            .options(selectinload(EscalationPath.levels))
            .order_by(EscalationPath.name)
        )
        return list(result.scalars().all())

    async def resolve_path_for_project(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        explicit_path_id: Optional[uuid.UUID] = None,
    ) -> Optional[EscalationPath]:
        """
        Resolve which escalation path applies to a project submission.

        Resolution order:
          1. explicit_path_id (project.escalation_path_id)
          2. org default path
          3. system template
        """
        if explicit_path_id:
            path = await self.get_path_with_levels(explicit_path_id)
            if path and path.is_active:
                return path
        org_default = await self.get_org_default_path(org_id)
        if org_default:
            return org_default
        return await self.get_system_template()

    # ── Path writes ───────────────────────────────────────────────────────────

    async def create_path(self, path: EscalationPath) -> EscalationPath:
        self.db.add(path)
        await self.db.flush()
        return path

    async def save_path(self, path: EscalationPath) -> EscalationPath:
        self.db.add(path)
        await self.db.flush()
        return path

    async def clear_org_default(self, org_id: uuid.UUID, exclude_id: Optional[uuid.UUID] = None) -> None:
        """Clear is_default on all org paths except exclude_id."""
        q = select(EscalationPath).where(
            EscalationPath.org_id == org_id,
            EscalationPath.is_default == True,  # noqa: E712
        )
        result = await self.db.execute(q)
        for path in result.scalars().all():
            if path.id != exclude_id:
                path.is_default = False
                self.db.add(path)
        await self.db.flush()

    # ── Level reads ───────────────────────────────────────────────────────────

    async def get_level(self, level_id: uuid.UUID) -> Optional[EscalationLevel]:
        result = await self.db.execute(
            select(EscalationLevel).where(EscalationLevel.id == level_id)
        )
        return result.scalar_one_or_none()

    # ── Level writes ──────────────────────────────────────────────────────────

    async def create_level(self, level: EscalationLevel) -> EscalationLevel:
        self.db.add(level)
        await self.db.flush()
        return level

    async def save_level(self, level: EscalationLevel) -> EscalationLevel:
        self.db.add(level)
        await self.db.flush()
        return level

    async def delete_level(self, level: EscalationLevel) -> None:
        await self.db.delete(level)
        await self.db.flush()

    async def reorder_levels(
        self,
        path_id: uuid.UUID,
        ordered_level_ids: List[uuid.UUID],
    ) -> None:
        """
        Reassign level_order values based on the provided ordered list.
        ordered_level_ids[0] → level_order=1, [1] → level_order=2, etc.
        """
        for order, level_id in enumerate(ordered_level_ids, start=1):
            result = await self.db.execute(
                select(EscalationLevel).where(
                    EscalationLevel.path_id == path_id,
                    EscalationLevel.id == level_id,
                )
            )
            level = result.scalar_one_or_none()
            if level:
                level.level_order = order
                self.db.add(level)
        await self.db.flush()
