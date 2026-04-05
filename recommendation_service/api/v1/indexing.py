"""api/v1/indexing.py — Manual indexing endpoints (internal/admin)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from core.dependencies import DbDep, require_internal_key
from models.entity import ActivityEvent
from repositories.entity_repository import EntityRepository
from schemas.recommendation import IndexActivityRequest, IndexEntityRequest
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
