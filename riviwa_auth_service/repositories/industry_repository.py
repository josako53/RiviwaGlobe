# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/industry_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/industry_repository.py
═══════════════════════════════════════════════════════════════════════════════
Pure DB access for:
  Industry                — master list of industries
  OrganisationIndustry    — M2M: org ↔ industry
  IndustryFieldTemplate   — pre-built field definitions per industry

Design rules:
  · Zero business logic.
  · Returns None for not-found rows.
  · flush() only — commit is owned by the service layer.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.industry import Industry, IndustryFieldTemplate, OrganisationIndustry

log = structlog.get_logger(__name__)


class IndustryRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Industry lookups ──────────────────────────────────────────────────────

    async def list_industries(self, active_only: bool = True) -> list[Industry]:
        q = select(Industry)
        if active_only:
            q = q.where(Industry.is_active == True)  # noqa: E712
        q = q.order_by(Industry.sort_order, Industry.name)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_industry_by_id(self, industry_id: uuid.UUID) -> Optional[Industry]:
        result = await self.db.execute(
            select(Industry).where(Industry.id == industry_id)
        )
        return result.scalar_one_or_none()

    async def get_industry_by_slug(self, slug: str) -> Optional[Industry]:
        result = await self.db.execute(
            select(Industry).where(Industry.slug == slug)
        )
        return result.scalar_one_or_none()

    # ── OrganisationIndustry ──────────────────────────────────────────────────

    async def list_org_industries(self, org_id: uuid.UUID) -> list[OrganisationIndustry]:
        """Return all OrganisationIndustry rows for an org, with the related Industry joined."""
        result = await self.db.execute(
            select(OrganisationIndustry)
            .options(selectinload(OrganisationIndustry.industry))
            .where(OrganisationIndustry.org_id == org_id)
            .order_by(OrganisationIndustry.created_at)
        )
        return list(result.scalars().all())

    async def set_org_industries(
        self,
        org_id: uuid.UUID,
        industry_ids: list[uuid.UUID],
        primary_id: Optional[uuid.UUID] = None,
    ) -> list[OrganisationIndustry]:
        """Replace all org-industry associations atomically."""
        # Delete existing
        existing_result = await self.db.execute(
            select(OrganisationIndustry).where(OrganisationIndustry.org_id == org_id)
        )
        for row in existing_result.scalars().all():
            await self.db.delete(row)
        await self.db.flush()

        # Insert new
        new_rows: list[OrganisationIndustry] = []
        for ind_id in industry_ids:
            row = OrganisationIndustry(
                org_id=org_id,
                industry_id=ind_id,
                is_primary=(ind_id == primary_id) if primary_id else False,
            )
            self.db.add(row)
            new_rows.append(row)

        await self.db.flush()
        for row in new_rows:
            await self.db.refresh(row)
        return new_rows

    async def add_org_industry(
        self,
        org_id: uuid.UUID,
        industry_id: uuid.UUID,
        is_primary: bool = False,
    ) -> OrganisationIndustry:
        row = OrganisationIndustry(
            org_id=org_id,
            industry_id=industry_id,
            is_primary=is_primary,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def remove_org_industry(self, org_id: uuid.UUID, industry_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(OrganisationIndustry).where(
                and_(
                    OrganisationIndustry.org_id == org_id,
                    OrganisationIndustry.industry_id == industry_id,
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.db.delete(row)
        await self.db.flush()
        return True

    async def get_org_industry(
        self, org_id: uuid.UUID, industry_id: uuid.UUID
    ) -> Optional[OrganisationIndustry]:
        result = await self.db.execute(
            select(OrganisationIndustry).where(
                and_(
                    OrganisationIndustry.org_id == org_id,
                    OrganisationIndustry.industry_id == industry_id,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── IndustryFieldTemplate ─────────────────────────────────────────────────

    async def get_field_templates(
        self,
        industry_id: uuid.UUID,
        entity_type: Optional[str] = None,
    ) -> list[IndustryFieldTemplate]:
        q = select(IndustryFieldTemplate).where(
            IndustryFieldTemplate.industry_id == industry_id
        )
        if entity_type:
            q = q.where(IndustryFieldTemplate.entity_type == entity_type)
        q = q.order_by(IndustryFieldTemplate.sort_order, IndustryFieldTemplate.field_key)
        result = await self.db.execute(q)
        return list(result.scalars().all())
