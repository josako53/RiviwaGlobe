# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/custom_field_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/custom_field_repository.py
═══════════════════════════════════════════════════════════════════════════════
Pure DB access for OrgCustomFieldDefinition.

Design rules:
  · Zero business logic.
  · Returns None for not-found rows.
  · flush() only — commit is owned by the service layer.
  · Soft-delete via is_active=False.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.industry import IndustryFieldTemplate, OrgCustomFieldDefinition

log = structlog.get_logger(__name__)


class CustomFieldRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        entity_type: Optional[str] = None,
        active_only: bool = True,
    ) -> list[OrgCustomFieldDefinition]:
        q = select(OrgCustomFieldDefinition).where(
            OrgCustomFieldDefinition.org_id == org_id
        )
        if entity_type:
            q = q.where(OrgCustomFieldDefinition.entity_type == entity_type)
        if active_only:
            q = q.where(OrgCustomFieldDefinition.is_active == True)  # noqa: E712
        q = q.order_by(
            OrgCustomFieldDefinition.entity_type,
            OrgCustomFieldDefinition.sort_order,
            OrgCustomFieldDefinition.field_key,
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Get by ID ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self, field_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[OrgCustomFieldDefinition]:
        result = await self.db.execute(
            select(OrgCustomFieldDefinition).where(
                and_(
                    OrgCustomFieldDefinition.id == field_id,
                    OrgCustomFieldDefinition.org_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        org_id: uuid.UUID,
        entity_type: str,
        field_key: str,
        label: str,
        field_type: str,
        created_by_id: Optional[uuid.UUID],
        **kwargs: Any,
    ) -> OrgCustomFieldDefinition:
        field = OrgCustomFieldDefinition(
            org_id=org_id,
            entity_type=entity_type,
            field_key=field_key,
            label=label,
            field_type=field_type,
            created_by_id=created_by_id,
            **kwargs,
        )
        self.db.add(field)
        await self.db.flush()
        await self.db.refresh(field)
        return field

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(
        self, field: OrgCustomFieldDefinition, **fields: Any
    ) -> OrgCustomFieldDefinition:
        for key, value in fields.items():
            setattr(field, key, value)
        await self.db.flush()
        await self.db.refresh(field)
        return field

    # ── Soft delete ───────────────────────────────────────────────────────────

    async def delete(self, field_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        field = await self.get_by_id(field_id, org_id)
        if not field:
            return False
        field.is_active = False
        await self.db.flush()
        return True

    # ── Bulk import from template ─────────────────────────────────────────────

    async def import_from_template(
        self,
        org_id: uuid.UUID,
        templates: list[IndustryFieldTemplate],
        created_by_id: Optional[uuid.UUID],
    ) -> list[OrgCustomFieldDefinition]:
        """
        Bulk-import IndustryFieldTemplate rows into OrgCustomFieldDefinition.
        Skips rows where (org_id, entity_type, field_key) already exists.
        Returns newly created rows only.
        """
        # Fetch existing keys to skip
        existing_result = await self.db.execute(
            select(
                OrgCustomFieldDefinition.entity_type,
                OrgCustomFieldDefinition.field_key,
            ).where(OrgCustomFieldDefinition.org_id == org_id)
        )
        existing_keys: set[tuple[str, str]] = {
            (row.entity_type, row.field_key) for row in existing_result.all()
        }

        created: list[OrgCustomFieldDefinition] = []
        for tmpl in templates:
            key = (tmpl.entity_type, tmpl.field_key)
            if key in existing_keys:
                continue

            field = OrgCustomFieldDefinition(
                org_id=org_id,
                entity_type=tmpl.entity_type,
                field_key=tmpl.field_key,
                label=tmpl.label,
                label_sw=tmpl.label_sw,
                field_type=tmpl.field_type,
                options=tmpl.options,
                placeholder=tmpl.placeholder,
                help_text=tmpl.help_text,
                is_required=tmpl.is_required,
                is_visible_to_consumer=tmpl.is_visible_to_consumer,
                feedback_types=tmpl.feedback_types,
                industry_template_key=None,  # set by service if needed
                sort_order=tmpl.sort_order,
                is_active=True,
                created_by_id=created_by_id,
            )
            self.db.add(field)
            existing_keys.add(key)
            created.append(field)

        if created:
            await self.db.flush()
            for f in created:
                await self.db.refresh(f)

        return created
