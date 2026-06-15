"""
services/industry_service.py
─────────────────────────────────────────────────────────────────────────────
Business logic for industry taxonomy, org-industry associations, and
custom field definition management (including template application).
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from events.publisher import EventPublisher
from models.industry import (
    Industry,
    IndustryFieldTemplate,
    OrgCustomFieldDefinition,
    OrganisationIndustry,
)
from repositories.custom_field_repository import CustomFieldRepository
from repositories.industry_repository import IndustryRepository

log = structlog.get_logger(__name__)


class IndustryService:

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db        = db
        self.publisher = publisher
        self._repo     = IndustryRepository(db)
        self._cf_repo  = CustomFieldRepository(db)

    # ── Industry ──────────────────────────────────────────────────────────────

    async def list_industries(self, active_only: bool = True) -> list[Industry]:
        return await self._repo.list_industries(active_only=active_only)

    async def get_industry_or_404(self, industry_id: uuid.UUID) -> Industry:
        industry = await self._repo.get_industry_by_id(industry_id)
        if not industry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {industry_id} not found.",
            )
        return industry

    # ── Org industries ────────────────────────────────────────────────────────

    async def get_org_industries(self, org_id: uuid.UUID) -> list[OrganisationIndustry]:
        return await self._repo.list_org_industries(org_id)

    async def set_org_industries(
        self,
        org_id: uuid.UUID,
        industry_ids: list[uuid.UUID],
        primary_id: Optional[uuid.UUID] = None,
    ) -> list[OrganisationIndustry]:
        """Replace all org-industry associations. Validates all IDs exist first."""
        # Validate all IDs
        for ind_id in industry_ids:
            industry = await self._repo.get_industry_by_id(ind_id)
            if not industry:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Industry {ind_id} not found.",
                )

        if primary_id and primary_id not in industry_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="primary_industry_id must be in the industry_ids list.",
            )

        rows = await self._repo.set_org_industries(
            org_id=org_id,
            industry_ids=industry_ids,
            primary_id=primary_id,
        )
        await self.db.commit()
        return rows

    async def add_org_industry(
        self,
        org_id: uuid.UUID,
        industry_id: uuid.UUID,
        is_primary: bool = False,
    ) -> OrganisationIndustry:
        await self.get_industry_or_404(industry_id)

        # Check not already linked
        existing = await self._repo.get_org_industry(org_id, industry_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This industry is already linked to the organisation.",
            )

        row = await self._repo.add_org_industry(
            org_id=org_id, industry_id=industry_id, is_primary=is_primary
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def remove_org_industry(
        self, org_id: uuid.UUID, industry_id: uuid.UUID
    ) -> bool:
        removed = await self._repo.remove_org_industry(org_id, industry_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Industry association not found for this organisation.",
            )
        await self.db.commit()
        return True

    # ── Field templates ───────────────────────────────────────────────────────

    async def get_field_templates(
        self,
        industry_id: uuid.UUID,
        entity_type: Optional[str] = None,
    ) -> list[IndustryFieldTemplate]:
        await self.get_industry_or_404(industry_id)
        return await self._repo.get_field_templates(
            industry_id=industry_id, entity_type=entity_type
        )

    # ── Apply template to org ─────────────────────────────────────────────────

    async def apply_template_to_org(
        self,
        org_id: uuid.UUID,
        industry_id: uuid.UUID,
        entity_type: Optional[str],
        created_by_id: Optional[uuid.UUID],
    ) -> list[OrgCustomFieldDefinition]:
        """
        Import IndustryFieldTemplate rows into OrgCustomFieldDefinition for an org.
        Skips any fields already defined (by entity_type + field_key uniqueness).
        Returns list of newly created OrgCustomFieldDefinition rows.
        """
        industry = await self.get_industry_or_404(industry_id)
        templates = await self._repo.get_field_templates(
            industry_id=industry_id, entity_type=entity_type
        )
        if not templates:
            return []

        # Set industry_template_key on each created field
        created = await self._cf_repo.import_from_template(
            org_id=org_id,
            templates=templates,
            created_by_id=created_by_id,
        )
        # Back-fill template key
        for field in created:
            field.industry_template_key = industry.slug
        await self.db.flush()
        await self.db.commit()
        for field in created:
            await self.db.refresh(field)
        return created
