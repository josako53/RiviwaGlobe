"""
repositories/address_repository.py
═══════════════════════════════════════════════════════════════════════════════
All DB operations for the addresses table.

Design rules
────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found; service layer raises exceptions.
  · Uses flush() only — commit owned by service layer / session dependency.
  · All writes use targeted UPDATE via SQLAlchemy update() where possible.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.address import Address

log = structlog.get_logger(__name__)


class AddressRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, address_id: uuid.UUID) -> Optional[Address]:
        result = await self.db.execute(
            select(Address).where(Address.id == address_id)
        )
        return result.scalar_one_or_none()

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> List[Address]:
        result = await self.db.execute(
            select(Address)
            .where(
                Address.entity_type == entity_type,
                Address.entity_id   == entity_id,
            )
            .order_by(Address.is_default.desc(), Address.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_default(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Optional[Address]:
        result = await self.db.execute(
            select(Address).where(
                Address.entity_type == entity_type,
                Address.entity_id   == entity_id,
                Address.is_default  == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_place_id(
        self,
        place_id: int,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Optional[Address]:
        """Check if this Nominatim place already exists for the entity."""
        result = await self.db.execute(
            select(Address).where(
                Address.place_id    == place_id,
                Address.entity_type == entity_type,
                Address.entity_id   == entity_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).where(
                Address.entity_type == entity_type,
                Address.entity_id   == entity_id,
            )
        )
        return result.scalar_one()

    # ── Writes ────────────────────────────────────────────────────────────────

    async def create(self, address: Address) -> Address:
        self.db.add(address)
        await self.db.flush()
        await self.db.refresh(address)
        return address

    async def update_fields(
        self,
        address_id: uuid.UUID,
        fields: dict,
    ) -> Optional[Address]:
        if not fields:
            return await self.get_by_id(address_id)
        await self.db.execute(
            update(Address)
            .where(Address.id == address_id)
            .values(**fields)
        )
        await self.db.flush()
        return await self.get_by_id(address_id)

    async def clear_defaults(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Unset is_default=True on all addresses for this entity except exclude_id."""
        stmt = (
            update(Address)
            .where(
                Address.entity_type == entity_type,
                Address.entity_id   == entity_id,
                Address.is_default  == True,  # noqa: E712
            )
            .values(is_default=False)
        )
        if exclude_id:
            stmt = stmt.where(Address.id != exclude_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def delete(self, address: Address) -> None:
        await self.db.delete(address)
        await self.db.flush()
