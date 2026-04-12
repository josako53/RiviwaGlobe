"""
services/obsidian_rag_service.py — Obsidian vault knowledge base for RAG.

Indexes all .md files from the configured vault path into Qdrant collection
'riviwa_knowledge'. Used to answer questions about GRM procedures, policies,
and analytics using the organization's own knowledge base.
"""
from __future__ import annotations
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
import structlog
from core.config import settings

log = structlog.get_logger(__name__)

# shared embedding model (same one as rag_service.py — lazy global)
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
            log.info("obsidian_rag.model_loaded", model=settings.EMBEDDING_MODEL)
        except Exception as exc:
            log.error("obsidian_rag.model_failed", error=str(exc))
    return _model


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            _qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        except Exception as exc:
            log.error("obsidian_rag.qdrant_failed", error=str(exc))
    return _qdrant_client


class ObsidianRAGService:
    VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output size
    COLLECTION = settings.QDRANT_COLLECTION_KNOWLEDGE

    def _ensure_collection(self) -> bool:
        client = _get_qdrant()
        if not client:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams
            existing = [c.name for c in client.get_collections().collections]
            if self.COLLECTION not in existing:
                client.create_collection(
                    collection_name=self.COLLECTION,
                    vectors_config=VectorParams(size=self.VECTOR_SIZE, distance=Distance.COSINE),
                )
                log.info("obsidian_rag.collection_created", name=self.COLLECTION)
            return True
        except Exception as exc:
            log.error("obsidian_rag.ensure_collection_failed", error=str(exc))
            return False

    def _chunk_markdown(self, content: str, file_path: str) -> List[dict]:
        """Split markdown into chunks by headers. Each chunk = {text, source, chunk_id}."""
        # Split on #, ##, or ### headers
        sections = re.split(r'\n(?=#{1,3} )', content.strip())
        chunks = []
        max_words = settings.RAG_CHUNK_SIZE_WORDS
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            words = section.split()
            # If section too long, sub-chunk by paragraphs
            if len(words) > max_words:
                paragraphs = section.split('\n\n')
                current: List[str] = []
                for para in paragraphs:
                    current.append(para)
                    if len(' '.join(current).split()) >= max_words:
                        chunks.append({
                            'text': '\n\n'.join(current).strip(),
                            'source': os.path.basename(file_path),
                            'chunk_id': f"{file_path}:{len(chunks)}",
                        })
                        current = []
                if current:
                    chunks.append({
                        'text': '\n\n'.join(current).strip(),
                        'source': os.path.basename(file_path),
                        'chunk_id': f"{file_path}:{len(chunks)}",
                    })
            else:
                chunks.append({
                    'text': section.strip(),
                    'source': os.path.basename(file_path),
                    'chunk_id': f"{file_path}:{i}",
                })
        return chunks

    def index_vault(self) -> int:
        """
        Scan vault directory, chunk all .md files, embed, and upsert to Qdrant.
        Returns number of chunks indexed.
        """
        vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
        if not vault_path.exists():
            log.warning("obsidian_rag.vault_not_found", path=str(vault_path))
            return 0
        if not self._ensure_collection():
            return 0
        model = _get_model()
        client = _get_qdrant()
        if not model or not client:
            return 0

        md_files = list(vault_path.rglob("*.md"))
        if not md_files:
            log.info("obsidian_rag.no_md_files", path=str(vault_path))
            return 0

        from qdrant_client.models import PointStruct
        total = 0
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                chunks = self._chunk_markdown(content, str(md_file))
                points = []
                for chunk in chunks:
                    if len(chunk['text'].split()) < 10:  # skip tiny chunks
                        continue
                    vector = model.encode(chunk['text']).tolist()
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk['chunk_id']))
                    points.append(PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            'text': chunk['text'],
                            'source': chunk['source'],
                            'chunk_id': chunk['chunk_id'],
                            'file': str(md_file.relative_to(vault_path)),
                        }
                    ))
                if points:
                    client.upsert(collection_name=self.COLLECTION, points=points)
                    total += len(points)
                    log.info("obsidian_rag.file_indexed", file=str(md_file.name), chunks=len(points))
            except Exception as exc:
                log.error("obsidian_rag.file_failed", file=str(md_file), error=str(exc))

        log.info("obsidian_rag.vault_indexed", total_chunks=total, files=len(md_files))
        return total

    def search(self, query: str, top_k: int = None) -> List[Tuple[str, float, str]]:
        """
        Search knowledge base for relevant chunks.
        Returns list of (text, score, source).
        """
        k = top_k or settings.RAG_TOP_K
        model = _get_model()
        client = _get_qdrant()
        if not model or not client:
            return []
        if not self._ensure_collection():
            return []
        try:
            vector = model.encode(query).tolist()
            results = client.search(
                collection_name=self.COLLECTION,
                query_vector=vector,
                limit=k,
                score_threshold=0.3,
            )
            return [(r.payload.get('text', ''), r.score, r.payload.get('source', '')) for r in results]
        except Exception as exc:
            log.error("obsidian_rag.search_failed", error=str(exc))
            return []

    def format_context(self, results: List[Tuple[str, float, str]]) -> str:
        """Format search results as context block for Groq/Ollama prompt."""
        if not results:
            return ""
        lines = ["--- KNOWLEDGE BASE CONTEXT ---"]
        for text, score, source in results:
            lines.append(f"[Source: {source}]\n{text}")
        lines.append("--- END CONTEXT ---")
        return "\n\n".join(lines)


_obsidian_rag: Optional[ObsidianRAGService] = None


def get_obsidian_rag() -> ObsidianRAGService:
    global _obsidian_rag
    if _obsidian_rag is None:
        _obsidian_rag = ObsidianRAGService()
    return _obsidian_rag
