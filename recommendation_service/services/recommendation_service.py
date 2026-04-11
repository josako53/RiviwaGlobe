"""
services/recommendation_service.py — Orchestrator.

Combines all signals: Qdrant ANN → DB load → scoring → caching.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import EntityNotFoundError
from models.entity import RecommendationEntity
from repositories.entity_repository import EntityRepository
from schemas.recommendation import (
    InteractionSummary,
    NearbyResponse,
    RecommendationResponse,
    RecommendedEntity,
    SimilarResponse,
)
from services import cache_service, embedding_service
from services.scoring_engine import score_candidates
from services.tag_service import build_idf_map

log = structlog.get_logger(__name__)


class RecommendationOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepository(db)

    async def get_recommendations(
        self,
        entity_id: uuid.UUID,
        limit: int = 20,
        page: int = 1,
        min_score: float = 0.1,
        entity_type: Optional[str] = None,
        category_filter: Optional[str] = None,
        geo_only: bool = False,
        include_explanation: bool = False,
    ) -> RecommendationResponse:
        """Full recommendation pipeline for an entity."""

        # Check cache
        cache_params = {
            "limit": limit, "page": page, "min_score": min_score,
            "entity_type": entity_type, "category": category_filter,
            "geo_only": geo_only,
        }
        cached = await cache_service.get_cached("recs", str(entity_id), cache_params)
        if cached:
            return RecommendationResponse(**cached, cache_hit=True)

        # Load query entity
        query_entity = await self.repo.get_by_id(entity_id)
        if not query_entity:
            raise EntityNotFoundError()

        # Stage 1: Get ANN candidates from Qdrant
        semantic_scores = {}
        candidate_ids = []

        if embedding_service.is_model_loaded() and embedding_service.is_qdrant_available():
            text = embedding_service.build_entity_text({
                "name": query_entity.name,
                "description": query_entity.description,
                "category": query_entity.category,
                "sector": query_entity.sector,
                "region": query_entity.region,
                "tags": query_entity.tags,
            })
            vector = embedding_service.encode(text)

            qdrant_filter = {}
            if entity_type:
                qdrant_filter["entity_type"] = entity_type
            if category_filter:
                qdrant_filter["category"] = category_filter

            ann_results = embedding_service.search_similar(
                vector=vector,
                limit=min(limit * 5, 200),
                filter_conditions=qdrant_filter if qdrant_filter else None,
            )
            for r in ann_results:
                semantic_scores[r["id"]] = r["score"]
                try:
                    candidate_ids.append(uuid.UUID(r["id"]))
                except ValueError:
                    pass

        # Fallback: if no Qdrant results, use DB-based candidates
        if not candidate_ids:
            db_candidates = await self.repo.get_candidates(
                exclude_id=entity_id,
                entity_type=entity_type,
                category=category_filter,
                region=query_entity.region if geo_only else None,
                limit=min(limit * 5, 200),
            )
            candidate_ids = [c.id for c in db_candidates]

        # Stage 2: Load full candidate entities from DB
        candidates = await self.repo.bulk_get(candidate_ids)

        # Geo filter
        if geo_only and query_entity.region:
            candidates = [
                c for c in candidates
                if c.region and c.region.lower() == query_entity.region.lower()
            ]

        # Build IDF map for tag scoring
        all_tags = await self.repo.get_all_tag_sets()
        idf_map = build_idf_map(all_tags) if all_tags else None

        # Stage 3: Score
        scored = score_candidates(
            query_entity=query_entity,
            candidates=candidates,
            semantic_scores=semantic_scores,
            idf_map=idf_map,
            include_explanation=include_explanation,
        )

        # Filter by min_score
        scored = [r for r in scored if r.score >= min_score]

        # Paginate
        total = len(scored)
        start = (page - 1) * limit
        page_results = scored[start:start + limit]

        response = RecommendationResponse(
            entity_id=entity_id,
            recommendations=page_results,
            total=total,
            page=page,
            page_size=limit,
            generated_at=datetime.now(timezone.utc),
            cache_hit=False,
        )

        # Cache
        await cache_service.set_cached(
            "recs", str(entity_id),
            response.model_dump(mode="json"),
            cache_params,
        )

        return response

    async def get_similar(
        self,
        entity_id: uuid.UUID,
        limit: int = 20,
        page: int = 1,
    ) -> SimilarResponse:
        """Pure semantic similarity — ignores geo."""

        query_entity = await self.repo.get_by_id(entity_id)
        if not query_entity:
            raise EntityNotFoundError()

        results: list[RecommendedEntity] = []

        if embedding_service.is_model_loaded() and embedding_service.is_qdrant_available():
            text = embedding_service.build_entity_text({
                "name": query_entity.name,
                "description": query_entity.description,
                "category": query_entity.category,
                "sector": query_entity.sector,
                "tags": query_entity.tags,
            })
            vector = embedding_service.encode(text)
            ann_results = embedding_service.search_similar(vector=vector, limit=limit * 2)

            cand_ids = []
            score_map = {}
            for r in ann_results:
                try:
                    cid = uuid.UUID(r["id"])
                    if cid != entity_id:
                        cand_ids.append(cid)
                        score_map[str(cid)] = r["score"]
                except ValueError:
                    pass

            candidates = await self.repo.bulk_get(cand_ids)
            for c in candidates:
                if c.status != "active":
                    continue
                results.append(RecommendedEntity(
                    entity_id=c.id,
                    entity_type=c.entity_type,
                    name=c.name,
                    slug=c.slug,
                    description=c.description,
                    category=c.category,
                    sector=c.sector,
                    cover_image_url=c.cover_image_url,
                    region=c.region,
                    country_code=c.country_code,
                    score=round(score_map.get(str(c.id), 0.0), 4),
                    interactions=None,
                ))

            results.sort(key=lambda r: r.score, reverse=True)

        total = len(results)
        start = (page - 1) * limit
        return SimilarResponse(
            entity_id=entity_id,
            similar=results[start:start + limit],
            total=total,
            page=page,
            page_size=limit,
            generated_at=datetime.now(timezone.utc),
        )

    async def discover_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        entity_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
    ) -> NearbyResponse:
        """Geo-based discovery."""

        from services.geo_service import haversine_km

        entities = await self.repo.get_nearby(
            lat=latitude, lon=longitude,
            radius_km=radius_km,
            entity_type=entity_type,
            category=category,
            limit=min(limit * 3, 200),
        )

        results: list[RecommendedEntity] = []
        for e in entities:
            if e.status != "active":
                continue
            dist = None
            if e.latitude is not None and e.longitude is not None:
                dist = haversine_km(latitude, longitude, e.latitude, e.longitude)

            results.append(RecommendedEntity(
                entity_id=e.id,
                entity_type=e.entity_type,
                name=e.name,
                slug=e.slug,
                description=e.description,
                category=e.category,
                sector=e.sector,
                cover_image_url=e.cover_image_url,
                org_logo_url=e.org_logo_url,
                latitude=e.latitude,
                longitude=e.longitude,
                city=e.city,
                region=e.region,
                country_code=e.country_code,
                distance_km=round(dist, 1) if dist else None,
                score=1.0 / (1.0 + (dist or 1000)),
                interactions=InteractionSummary(
                    feedback_count=e.feedback_count,
                    grievance_count=e.grievance_count,
                    suggestion_count=e.suggestion_count,
                    applause_count=e.applause_count,
                    engagement_count=e.engagement_count,
                ),
                accepts_grievances=e.accepts_grievances,
                accepts_suggestions=e.accepts_suggestions,
                accepts_applause=e.accepts_applause,
            ))

        results.sort(key=lambda r: r.distance_km if r.distance_km is not None else 99999)
        total = len(results)
        start = (page - 1) * limit

        return NearbyResponse(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            results=results[start:start + limit],
            total=total,
            page=page,
            page_size=limit,
            generated_at=datetime.now(timezone.utc),
        )
