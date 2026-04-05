# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/project_image_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/project_image_repository.py
────────────────────────────────────────────────────────────────────────────
All DB operations for ProjectProgressImage.

entity_type values:
  "project"    → OrgProject.id
  "subproject" → OrgSubProject.id
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.org_project import ProjectProgressImage


class ProjectImageRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, image: ProjectProgressImage) -> ProjectProgressImage:
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        image_id:    uuid.UUID,
        entity_type: Optional[str] = None,
        entity_id:   Optional[uuid.UUID] = None,
    ) -> Optional[ProjectProgressImage]:
        q = select(ProjectProgressImage).where(
            ProjectProgressImage.id == image_id,
            ProjectProgressImage.deleted_at.is_(None),
        )
        if entity_type:
            q = q.where(ProjectProgressImage.entity_type == entity_type)
        if entity_id:
            q = q.where(ProjectProgressImage.entity_id == entity_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        phase:       Optional[str] = None,
        skip:        int = 0,
        limit:       int = 50,
        include_deleted: bool = False,
    ) -> list[ProjectProgressImage]:
        q = (
            select(ProjectProgressImage)
            .where(
                ProjectProgressImage.entity_type == entity_type,
                ProjectProgressImage.entity_id   == entity_id,
            )
            .order_by(
                ProjectProgressImage.phase,
                ProjectProgressImage.display_order,
                ProjectProgressImage.captured_at.nullslast(),
                ProjectProgressImage.uploaded_at,
            )
        )
        if not include_deleted:
            q = q.where(ProjectProgressImage.deleted_at.is_(None))
        if phase:
            q = q.where(ProjectProgressImage.phase == phase)
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        phase:       Optional[str] = None,
    ) -> int:
        from sqlalchemy import func
        q = select(func.count(ProjectProgressImage.id)).where(
            ProjectProgressImage.entity_type == entity_type,
            ProjectProgressImage.entity_id   == entity_id,
            ProjectProgressImage.deleted_at.is_(None),
        )
        if phase:
            q = q.where(ProjectProgressImage.phase == phase)
        return await self.db.scalar(q) or 0

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        image:  ProjectProgressImage,
        fields: dict,
    ) -> ProjectProgressImage:
        _allowed = {"title", "description", "phase", "display_order",
                    "location_description", "gps_lat", "gps_lng",
                    "captured_at", "thumbnail_url"}
        for k, v in fields.items():
            if k in _allowed:
                setattr(image, k, v)
        self.db.add(image)
        return image

    # ── Soft delete ───────────────────────────────────────────────────────────

    async def soft_delete(self, image: ProjectProgressImage) -> None:
        """
        Soft-delete: sets deleted_at but never removes the object-storage file.
        Progress images are part of the project evidence trail.
        """
        image.deleted_at = datetime.utcnow()
        self.db.add(image)

    # ── Phase summary ─────────────────────────────────────────────────────────

    async def phase_counts(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict[str, int]:
        """Return {phase: count} for all non-deleted images."""
        from sqlalchemy import func
        q = (
            select(ProjectProgressImage.phase, func.count(ProjectProgressImage.id))
            .where(
                ProjectProgressImage.entity_type == entity_type,
                ProjectProgressImage.entity_id   == entity_id,
                ProjectProgressImage.deleted_at.is_(None),
            )
            .group_by(ProjectProgressImage.phase)
        )
        rows = await self.db.execute(q)
        return {phase: count for phase, count in rows.all()}
