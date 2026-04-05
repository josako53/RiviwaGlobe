"""services/embedding_service.py — Sentence-transformer embedding + Qdrant."""
from __future__ import annotations

import hashlib
from typing import Optional

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from core.config import settings

log = structlog.get_logger(__name__)

_model = None
_qdrant: Optional[QdrantClient] = None


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _qdrant


async def load_model() -> None:
    """Load the sentence-transformer model (call once at startup)."""
    global _model
    from sentence_transformers import SentenceTransformer
    log.info("embedding.model.loading", model=settings.EMBEDDING_MODEL)
    _model = SentenceTransformer(
        settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE,
    )
    log.info("embedding.model.loaded", dim=settings.EMBEDDING_DIM)


async def ensure_collection() -> None:
    """Create Qdrant collection if it doesn't exist."""
    client = get_qdrant()
    try:
        client.get_collection(settings.QDRANT_COLLECTION)
        log.info("qdrant.collection.exists", name=settings.QDRANT_COLLECTION)
    except (UnexpectedResponse, Exception):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        log.info("qdrant.collection.created", name=settings.QDRANT_COLLECTION)


def build_entity_text(entity: dict) -> str:
    """
    Combine entity fields into a rich text block for embedding.
    Order matters — most important signal first.
    """
    parts = [
        entity.get("name", ""),
        entity.get("description") or "",
        f"Category: {entity.get('category', '')}" if entity.get("category") else "",
        f"Sector: {entity.get('sector', '')}" if entity.get("sector") else "",
        f"Region: {entity.get('region', '')}" if entity.get("region") else "",
    ]
    tags = entity.get("tags")
    if tags:
        tag_list = tags if isinstance(tags, list) else tags.get("items", [])
        if tag_list:
            parts.append("Tags: " + ", ".join(tag_list))
    return " | ".join(p for p in parts if p)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def encode(text: str) -> list[float]:
    """Encode a single text into a vector."""
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    return _model.encode(text, normalize_embeddings=True).tolist()


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Batch encode texts."""
    if _model is None:
        raise RuntimeError("Embedding model not loaded.")
    return _model.encode(texts, normalize_embeddings=True).tolist()


def upsert_vector(entity_id: str, vector: list[float], payload: dict) -> None:
    """Upsert a single entity vector into Qdrant."""
    client = get_qdrant()
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=entity_id,
                vector=vector,
                payload=payload,
            )
        ],
    )


def delete_vector(entity_id: str) -> None:
    """Remove an entity from Qdrant."""
    client = get_qdrant()
    try:
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=[entity_id],
        )
    except Exception as exc:
        log.warning("qdrant.delete_failed", entity_id=entity_id, error=str(exc))


def search_similar(
    vector: list[float],
    limit: int = 50,
    score_threshold: float = 0.0,
    filter_conditions: dict | None = None,
) -> list[dict]:
    """
    ANN search in Qdrant. Returns list of {id, score, payload}.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = get_qdrant()
    query_filter = None
    if filter_conditions:
        conditions = []
        for key, value in filter_conditions.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        query_filter = Filter(must=conditions)

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vector,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=query_filter,
    )
    return [
        {"id": str(r.id), "score": r.score, "payload": r.payload or {}}
        for r in results
    ]


def is_model_loaded() -> bool:
    return _model is not None


def is_qdrant_available() -> bool:
    try:
        get_qdrant().get_collections()
        return True
    except Exception:
        return False
