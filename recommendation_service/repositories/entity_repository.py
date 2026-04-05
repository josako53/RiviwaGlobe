"""repositories/entity_repository.py — Database queries with geo support."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set

import structlog
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.entity import ActivityEvent, RecommendationEntity

log = structlog.get_logger(__name__)


class EntityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, entity_id: uuid.UUID) -> Optional[RecommendationEntity]:
        return await self.db.get(RecommendationEntity, entity_id)

    async def bulk_get(self, entity_ids: List[uuid.UUID]) -> List[RecommendationEntity]:
        if not entity_ids:
            return []
        result = await self.db.execute(
            select(RecommendationEntity).where(RecommendationEntity.id.in_(entity_ids))
        )
        return list(result.scalars().all())

    async def upsert(self, data: dict) -> RecommendationEntity:
        entity_id = data.get("id") or data.get("entity_id")
        existing = await self.get_by_id(entity_id) if entity_id else None

        if existing:
            for key, value in data.items():
                if key not in ("id", "entity_id", "created_at") and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            self.db.add(existing)
            await self.db.flush()
            return existing

        entity = RecommendationEntity(
            id=entity_id or uuid.uuid4(),
            **{k: v for k, v in data.items() if k != "entity_id" and hasattr(RecommendationEntity, k)},
        )
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update_status(self, entity_id: uuid.UUID, status: str) -> None:
        await self.db.execute(
            update(RecommendationEntity)
            .where(RecommendationEntity.id == entity_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        await self.db.flush()

    async def delete_entity(self, entity_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(RecommendationEntity).where(RecommendationEntity.id == entity_id)
        )
        await self.db.flush()

    async def add_activity(self, event: ActivityEvent) -> None:
        self.db.add(event)
        await self.db.flush()

    async def increment_feedback(
        self, entity_id: uuid.UUID, feedback_type: str | None = None,
    ) -> None:
        values = {
            "feedback_count": RecommendationEntity.feedback_count + 1,
            "last_active_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        if feedback_type == "grievance":
            values["grievance_count"] = RecommendationEntity.grievance_count + 1
        elif feedback_type == "suggestion":
            values["suggestion_count"] = RecommendationEntity.suggestion_count + 1
        elif feedback_type == "applause":
            values["applause_count"] = RecommendationEntity.applause_count + 1

        await self.db.execute(
            update(RecommendationEntity)
            .where(RecommendationEntity.id == entity_id)
            .values(**values)
        )
        await self.db.flush()

    async def increment_engagement(self, entity_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RecommendationEntity)
            .where(RecommendationEntity.id == entity_id)
            .values(
                engagement_count=RecommendationEntity.engagement_count + 1,
                last_active_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.flush()

    async def get_candidates(
        self,
        exclude_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        category: str | None = None,
        region: str | None = None,
        limit: int = 200,
    ) -> List[RecommendationEntity]:
        q = select(RecommendationEntity).where(RecommendationEntity.status == "active")
        if exclude_id:
            q = q.where(RecommendationEntity.id != exclude_id)
        if entity_type:
            q = q.where(RecommendationEntity.entity_type == entity_type)
        if category:
            q = q.where(RecommendationEntity.category == category)
        if region:
            q = q.where(RecommendationEntity.region == region)
        q = q.order_by(RecommendationEntity.feedback_count.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: float = 50.0,
        entity_type: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> List[RecommendationEntity]:
        """
        Geo-based query. Uses simple lat/lon bounding box for now.
        PostGIS ST_DWithin can be added when PostGIS extension is available.
        """
        # Approximate bounding box (1 degree lat ≈ 111km)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * max(0.01, abs(__import__("math").cos(__import__("math").radians(lat)))))

        q = (
            select(RecommendationEntity)
            .where(
                RecommendationEntity.status == "active",
                RecommendationEntity.latitude.isnot(None),
                RecommendationEntity.longitude.isnot(None),
                RecommendationEntity.latitude.between(lat - lat_delta, lat + lat_delta),
                RecommendationEntity.longitude.between(lon - lon_delta, lon + lon_delta),
            )
        )
        if entity_type:
            q = q.where(RecommendationEntity.entity_type == entity_type)
        if category:
            q = q.where(RecommendationEntity.category == category)
        q = q.limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_all_tag_sets(self) -> List[Set[str]]:
        """Get all entity tag sets for IDF computation."""
        result = await self.db.execute(
            select(
                RecommendationEntity.category,
                RecommendationEntity.sector,
                RecommendationEntity.tags,
            ).where(RecommendationEntity.status == "active")
        )
        tag_sets = []
        for row in result.all():
            tags: set[str] = set()
            if row.category:
                tags.add(row.category.lower())
            if row.sector:
                tags.add(row.sector.lower())
            if row.tags:
                items = row.tags if isinstance(row.tags, list) else row.tags.get("items", [])
                tags.update(t.lower() for t in items if isinstance(t, str))
            if tags:
                tag_sets.append(tags)
        return tag_sets

    async def mark_indexed(self, entity_id: uuid.UUID, text_hash: str) -> None:
        await self.db.execute(
            update(RecommendationEntity)
            .where(RecommendationEntity.id == entity_id)
            .values(is_indexed=True, embedding_text_hash=text_hash, updated_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
