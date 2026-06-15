"""
services/custom_field_service.py
─────────────────────────────────────────────────────────────────────────────
Business logic for per-org custom field definition CRUD.
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from events.publisher import EventPublisher
from models.industry import OrgCustomFieldDefinition
from repositories.custom_field_repository import CustomFieldRepository

log = structlog.get_logger(__name__)


class CustomFieldService:

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db        = db
        self.publisher = publisher
        self._repo     = CustomFieldRepository(db)

    async def list(
        self,
        org_id:      uuid.UUID,
        entity_type: Optional[str] = None,
        active_only: bool = True,
    ) -> list[OrgCustomFieldDefinition]:
        return await self._repo.list_for_org(
            org_id=org_id, entity_type=entity_type, active_only=active_only
        )

    async def create(
        self,
        org_id:        uuid.UUID,
        data:          dict,
        created_by_id: Optional[uuid.UUID],
    ) -> OrgCustomFieldDefinition:
        entity_type = data["entity_type"]
        field_key   = data["field_key"]

        # Uniqueness guard
        existing = await self._repo.list_for_org(
            org_id=org_id, entity_type=entity_type, active_only=False
        )
        for f in existing:
            if f.field_key == field_key:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A field with key '{field_key}' already exists for entity_type '{entity_type}'.",
                )

        field = await self._repo.create(
            org_id=org_id,
            entity_type=entity_type,
            field_key=field_key,
            label=data["label"],
            field_type=data.get("field_type", "text"),
            created_by_id=created_by_id,
            label_sw=data.get("label_sw"),
            options=data.get("options"),
            placeholder=data.get("placeholder"),
            help_text=data.get("help_text"),
            is_required=data.get("is_required", False),
            is_visible_to_consumer=data.get("is_visible_to_consumer", True),
            feedback_types=data.get("feedback_types"),
            sort_order=data.get("sort_order", 0),
        )
        await self.db.commit()
        await self.db.refresh(field)
        return field

    async def update(
        self,
        field_id: uuid.UUID,
        org_id:   uuid.UUID,
        data:     dict,
    ) -> OrgCustomFieldDefinition:
        field = await self._repo.get_by_id(field_id, org_id)
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom field not found.",
            )

        update_data = {k: v for k, v in data.items() if v is not None}
        if update_data:
            field = await self._repo.update(field, **update_data)
            await self.db.commit()
            await self.db.refresh(field)
        return field

    async def deactivate(
        self, field_id: uuid.UUID, org_id: uuid.UUID
    ) -> dict:
        deleted = await self._repo.delete(field_id, org_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom field not found.",
            )
        await self.db.commit()
        return {"detail": "Custom field deactivated."}
