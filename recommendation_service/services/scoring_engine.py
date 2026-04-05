"""
services/scoring_engine.py — Four-signal recommendation scoring.

final_score =
  (WEIGHT_SEMANTIC    x semantic_similarity)
+ (WEIGHT_TAG_OVERLAP x tag_overlap)
+ (WEIGHT_GEO         x geo_proximity)
+ (WEIGHT_RECENCY     x recency_score)
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from core.config import settings
from models.entity import RecommendationEntity
from schemas.recommendation import InteractionSummary, RecommendedEntity, ScoreBreakdown
from services.geo_service import compute_geo_score
from services.tag_service import compute_tag_score


def _recency_score(last_active_at: datetime | None) -> float:
    """Exponential decay: exp(-lambda * days_since_last_activity)."""
    if not last_active_at:
        return 0.0
    now = datetime.now(timezone.utc)
    if last_active_at.tzinfo is None:
        last_active_at = last_active_at.replace(tzinfo=timezone.utc)
    days = (now - last_active_at).total_seconds() / 86400
    return math.exp(-settings.RECENCY_LAMBDA * max(days, 0))


def _extract_tags(entity: RecommendationEntity) -> Set[str]:
    """Extract a flat set of tags from entity fields."""
    tags: set[str] = set()
    if entity.category:
        tags.add(entity.category.lower())
    if entity.sector:
        tags.add(entity.sector.lower())
    if entity.tags:
        items = entity.tags if isinstance(entity.tags, list) else entity.tags.get("items", [])
        tags.update(t.lower() for t in items if isinstance(t, str))
    return tags


def score_candidates(
    query_entity: RecommendationEntity,
    candidates: List[RecommendationEntity],
    semantic_scores: Dict[str, float],
    idf_map: Dict[str, float] | None = None,
    include_explanation: bool = False,
) -> List[RecommendedEntity]:
    """
    Score a list of candidate entities against the query entity.
    Returns sorted list of RecommendedEntity (highest score first).
    """
    query_tags = _extract_tags(query_entity)
    results: list[RecommendedEntity] = []

    for candidate in candidates:
        if candidate.id == query_entity.id:
            continue
        if candidate.status != "active":
            continue

        cid = str(candidate.id)

        # Signal 1: Semantic (from Qdrant ANN search)
        sem_score = semantic_scores.get(cid, 0.0)

        # Signal 2: Tag overlap
        cand_tags = _extract_tags(candidate)
        tag_score, shared_tags = compute_tag_score(query_tags, cand_tags, idf_map)

        # Signal 3: Geo proximity
        geo_score, distance_km = compute_geo_score(
            query_entity.latitude, query_entity.longitude,
            candidate.latitude, candidate.longitude,
            city1=query_entity.city, city2=candidate.city,
            region1=query_entity.region, region2=candidate.region,
            country1=query_entity.country_code, country2=candidate.country_code,
        )

        # Signal 4: Recency
        rec_score = _recency_score(candidate.last_active_at)

        # Final weighted score
        final = (
            settings.WEIGHT_SEMANTIC * sem_score
            + settings.WEIGHT_TAG_OVERLAP * tag_score
            + settings.WEIGHT_GEO_PROXIMITY * geo_score
            + settings.WEIGHT_RECENCY * rec_score
        )

        breakdown = None
        if include_explanation:
            breakdown = ScoreBreakdown(
                semantic=round(sem_score, 4),
                tag_overlap=round(tag_score, 4),
                geo_proximity=round(geo_score, 4),
                recency=round(rec_score, 4),
            )

        interactions = InteractionSummary(
            feedback_count=candidate.feedback_count,
            grievance_count=candidate.grievance_count,
            suggestion_count=candidate.suggestion_count,
            applause_count=candidate.applause_count,
            engagement_count=candidate.engagement_count,
        )

        results.append(RecommendedEntity(
            entity_id=candidate.id,
            entity_type=candidate.entity_type,
            name=candidate.name,
            slug=candidate.slug,
            description=candidate.description,
            category=candidate.category,
            sector=candidate.sector,
            cover_image_url=candidate.cover_image_url,
            org_logo_url=candidate.org_logo_url,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            city=candidate.city,
            region=candidate.region,
            country_code=candidate.country_code,
            status=candidate.status,
            score=round(final, 4),
            score_breakdown=breakdown,
            distance_km=round(distance_km, 1) if distance_km is not None else None,
            shared_tags=shared_tags,
            interactions=interactions,
            accepts_grievances=candidate.accepts_grievances,
            accepts_suggestions=candidate.accepts_suggestions,
            accepts_applause=candidate.accepts_applause,
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
