"""services/rag_service.py — RAG pipeline using Qdrant + sentence-transformers."""
from __future__ import annotations
import uuid
from typing import List, Optional, Tuple
import structlog
from core.config import settings

log = structlog.get_logger(__name__)

# ── Embedding model (lazy-loaded, shared with recommendation_service) ─────────
_model = None
_qdrant_client = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                cache_folder=settings.EMBEDDING_MODEL_PATH,
            )
            log.info("rag.embedding_model_loaded", model=settings.EMBEDDING_MODEL)
        except Exception as exc:
            log.error("rag.embedding_model_failed", error=str(exc))
            _model = None
    return _model


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            _qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            log.info("rag.qdrant_connected", host=settings.QDRANT_HOST)
        except Exception as exc:
            log.error("rag.qdrant_failed", error=str(exc))
            _qdrant_client = None
    return _qdrant_client


class RAGService:
    """
    Manages project knowledge base in Qdrant.
    Used to auto-identify which project a Consumer is referring to.
    """

    VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output size

    def _embed(self, text: str) -> Optional[List[float]]:
        model = _get_model()
        if model is None:
            return None
        try:
            return model.encode(text).tolist()
        except Exception as exc:
            log.warning("rag.embed_failed", error=str(exc))
            return None

    def _ensure_collection(self) -> bool:
        """Create Qdrant collection if it doesn't exist. Returns True on success."""
        client = _get_qdrant()
        if client is None:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams
            collections = [c.name for c in client.get_collections().collections]
            if settings.QDRANT_COLLECTION_PROJECTS not in collections:
                client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_PROJECTS,
                    vectors_config=VectorParams(size=self.VECTOR_SIZE, distance=Distance.COSINE),
                )
                log.info("rag.collection_created", name=settings.QDRANT_COLLECTION_PROJECTS)
            return True
        except Exception as exc:
            log.error("rag.ensure_collection_failed", error=str(exc))
            return False

    def index_project(self, project_id: uuid.UUID, searchable_text: str, metadata: dict) -> bool:
        """
        Add or update a project's embedding in Qdrant.
        metadata: {name, region, primary_lga, status, organisation_id, ...}
        """
        vector = self._embed(searchable_text)
        if vector is None:
            return False
        if not self._ensure_collection():
            return False
        try:
            from qdrant_client.models import PointStruct
            _get_qdrant().upsert(
                collection_name=settings.QDRANT_COLLECTION_PROJECTS,
                points=[
                    PointStruct(
                        id=str(project_id),
                        vector=vector,
                        payload={"project_id": str(project_id), **metadata},
                    )
                ],
            )
            return True
        except Exception as exc:
            log.error("rag.index_project_failed", project_id=str(project_id), error=str(exc))
            return False

    def remove_project(self, project_id: uuid.UUID) -> None:
        client = _get_qdrant()
        if client is None:
            return
        try:
            from qdrant_client.models import PointIdsList
            client.delete(
                collection_name=settings.QDRANT_COLLECTION_PROJECTS,
                points_selector=PointIdsList(points=[str(project_id)]),
            )
        except Exception as exc:
            log.warning("rag.remove_project_failed", project_id=str(project_id), error=str(exc))

    def search_projects(
        self, query: str, top_k: int = 3, score_threshold: float = 0.35
    ) -> List[Tuple[str, float, dict]]:
        """
        Semantic search for the most relevant projects matching a Consumer's location/description.
        Returns: list of (project_id_str, score, payload)
        """
        vector = self._embed(query)
        if vector is None:
            return []
        client = _get_qdrant()
        if client is None:
            return []
        # Ensure collection exists before searching (returns empty on fresh deploy)
        if not self._ensure_collection():
            return []
        try:
            results = client.search(
                collection_name=settings.QDRANT_COLLECTION_PROJECTS,
                query_vector=vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
            return [(str(r.id), r.score, r.payload or {}) for r in results]
        except Exception as exc:
            log.error("rag.search_failed", error=str(exc))
            return []

    def build_project_context(self, projects_data: list) -> str:
        """
        Format project knowledge for injection into the Ollama system prompt.
        projects_data: list of ProjectKnowledgeBase-like dicts
        """
        if not projects_data:
            return "No projects currently active."
        lines = []
        for p in projects_data:
            name    = p.get("name", "Unknown")
            region  = p.get("region", "")
            lga     = p.get("primary_lga", "")
            wards   = ", ".join(p.get("wards", []))
            stage   = p.get("active_stage_name", "")
            status  = p.get("status", "")
            pid     = p.get("project_id", "")
            line = f"- PROJECT: {name} | ID: {pid} | Region: {region} | LGA: {lga}"
            if wards:
                line += f" | Wards: {wards}"
            if stage:
                line += f" | Stage: {stage}"
            if status:
                line += f" | Status: {status}"
            lines.append(line)
        return "\n".join(lines)


# Global singleton
_rag: Optional[RAGService] = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
