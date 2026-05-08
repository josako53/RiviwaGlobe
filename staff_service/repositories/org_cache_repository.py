"""repositories/org_cache_repository.py — OrgCache DB operations."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.org_cache import OrgCache


class OrgCacheRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, org_id: UUID) -> Optional[OrgCache]:
        return await self.db.get(OrgCache, org_id)

    async def upsert(self, org_id: UUID, data: Dict[str, Any]) -> OrgCache:
        existing = await self.db.get(OrgCache, org_id)
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return existing
        else:
            obj = OrgCache(org_id=org_id, **data)
            self.db.add(obj)
            await self.db.flush()
            return obj
