"""api/v1/indexing.py — Manual indexing endpoints (internal/admin)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.dependencies import DbDep, require_internal_key
from models.entity import ActivityEvent
from repositories.entity_repository import EntityRepository
from schemas.recommendation import (
    EntityListResponse,
    EntityResponse,
    IndexActivityRequest,
    IndexEntityRequest,
)
from services import cache_service, embedding_service

router = APIRouter(prefix="/index", tags=["Indexing"], dependencies=[Depends(require_internal_key)])


@router.post(
    "/entity",
    summary="Index or update an entity",
    description="Manually index an entity for recommendations. Requires internal service key.",
)
async def index_entity(body: IndexEntityRequest, db: DbDep):
    repo = EntityRepository(db)
    data = body.model_dump(exclude_none=True)
    if body.tags:
        data["tags"] = {"items": body.tags}
    data["id"] = data.pop("entity_id")

    entity = await repo.upsert(data)

    # Embed in Qdrant
    if embedding_service.is_model_loaded():
        text = embedding_service.build_entity_text(data)
        vector = embedding_service.encode(text)
        embedding_service.upsert_vector(
            str(entity.id), vector,
            {"entity_type": body.entity_type, "category": body.category, "region": body.region},
        )
        await repo.mark_indexed(entity.id, embedding_service.text_hash(text))

    await db.commit()
    await cache_service.invalidate("recs", str(entity.id))
    return {"status": "indexed", "entity_id": str(entity.id)}


@router.put(
    "/entity/{entity_id}",
    summary="Update an indexed entity",
)
async def update_entity(entity_id: uuid.UUID, body: IndexEntityRequest, db: DbDep):
    body.entity_id = entity_id
    return await index_entity(body, db)


@router.delete(
    "/entity/{entity_id}",
    summary="Remove an entity from the index",
)
async def delete_entity(entity_id: uuid.UUID, db: DbDep):
    repo = EntityRepository(db)
    await repo.delete_entity(entity_id)
    embedding_service.delete_vector(str(entity_id))
    await db.commit()
    await cache_service.invalidate("recs", str(entity_id))
    return {"status": "deleted", "entity_id": str(entity_id)}


@router.post(
    "/activity",
    summary="Log an activity event",
    description="Manually log an activity event. Updates popularity scores.",
)
async def index_activity(body: IndexActivityRequest, db: DbDep):
    repo = EntityRepository(db)
    event = ActivityEvent(
        entity_id=body.entity_id,
        event_type=body.event_type,
        actor_id=body.actor_id,
        feedback_type=body.feedback_type,
        occurred_at=body.occurred_at or datetime.now(timezone.utc),
        payload=body.payload,
    )
    await repo.add_activity(event)

    if "feedback" in body.event_type:
        await repo.increment_feedback(body.entity_id, body.feedback_type)
    else:
        await repo.increment_engagement(body.entity_id)

    await db.commit()
    await cache_service.invalidate("recs", str(body.entity_id))
    return {"status": "recorded", "entity_id": str(body.entity_id)}


@router.get(
    "/entity/{entity_id}",
    response_model=EntityResponse,
    summary="Retrieve a single indexed entity",
    description="Returns full metadata for an indexed entity. Useful for verifying indexing correctness.",
)
async def get_entity(entity_id: uuid.UUID, db: DbDep) -> EntityResponse:
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found in recommendation index.")
    return EntityResponse.from_entity(entity)


@router.get(
    "/entities",
    response_model=EntityListResponse,
    summary="List all indexed entities",
    description=(
        "Returns a paginated list of all entities in the recommendation index. "
        "Supports filtering by entity_type, category, region, and status."
    ),
)
async def list_entities(
    db: DbDep,
    entity_type: Optional[str] = Query(default=None, description="project | organisation"),
    category: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, description="active | inactive | paused"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> EntityListResponse:
    repo = EntityRepository(db)
    offset = (page - 1) * page_size
    entities = await repo.list_entities(
        entity_type=entity_type,
        category=category,
        region=region,
        status=status,
        limit=page_size,
        offset=offset,
    )
    total = await repo.count_entities(
        entity_type=entity_type,
        category=category,
        region=region,
        status=status,
    )
    return EntityListResponse(
        items=[EntityResponse.from_entity(e) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
    )
