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

    # ── Generic entity collection helpers ────────────────────────────────────

    def _ensure_entity_collection(self, collection: str) -> bool:
        client = _get_qdrant()
        if client is None:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams
            existing = [c.name for c in client.get_collections().collections]
            if collection not in existing:
                client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=self.VECTOR_SIZE, distance=Distance.COSINE),
                )
                log.info("rag.entity_collection_created", name=collection)
            return True
        except Exception as exc:
            log.error("rag.entity_collection_failed", name=collection, error=str(exc))
            return False

    def index_entity(self, entity_id: str, collection: str, searchable_text: str, payload: dict) -> bool:
        """Upsert any entity (org/branch/dept/service/staff) into its Qdrant collection."""
        vector = self._embed(searchable_text)
        if vector is None:
            return False
        if not self._ensure_entity_collection(collection):
            return False
        try:
            from qdrant_client.models import PointStruct
            _get_qdrant().upsert(
                collection_name=collection,
                points=[PointStruct(id=entity_id, vector=vector, payload=payload)],
            )
            return True
        except Exception as exc:
            log.error("rag.index_entity_failed", entity_id=entity_id, collection=collection, error=str(exc))
            return False

    def remove_entity(self, entity_id: str, collection: str) -> None:
        client = _get_qdrant()
        if client is None:
            return
        try:
            from qdrant_client.models import PointIdsList
            client.delete(collection_name=collection,
                          points_selector=PointIdsList(points=[entity_id]))
        except Exception as exc:
            log.warning("rag.remove_entity_failed", entity_id=entity_id, collection=collection, error=str(exc))

    def search_entity(
        self, query: str, collection: str, top_k: int = 3, score_threshold: float = 0.60
    ) -> List[Tuple[str, float, dict]]:
        """Semantic search across any entity collection."""
        vector = self._embed(query)
        if vector is None:
            return []
        client = _get_qdrant()
        if client is None:
            return []
        if not self._ensure_entity_collection(collection):
            return []
        try:
            results = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
            return [(str(r.id), r.score, r.payload or {}) for r in results]
        except Exception as exc:
            log.error("rag.search_entity_failed", collection=collection, error=str(exc))
            return []

    # ── Convenience indexers (thin wrappers over index_entity) ───────────────

    def index_org(self, org_id: str, org: dict) -> bool:
        desc            = org.get("description", "") or ""
        vision          = org.get("vision", "") or ""
        mission         = org.get("mission", "") or ""
        objectives      = org.get("objectives", "") or ""
        functionalities = org.get("functionalities") or []
        func_text       = " ".join(
            str(f) for f in functionalities if isinstance(f, str)
        )[:300]
        faqs       = org.get("faqs") or []
        faq_text   = " ".join(
            f"{f.get('question', '')} {f.get('answer', '')}"
            for f in faqs if isinstance(f, dict)
        )[:500]
        industries = org.get("industries") or []
        industries_text = " ".join(
            i.get("name", "") for i in industries if isinstance(i, dict)
        )
        leadership = org.get("leadership") or []
        leadership_text = " ".join(
            f"{l.get('full_name', '')} {l.get('role_title', '')}"
            for l in leadership if isinstance(l, dict)
        )[:300]
        hours = org.get("operating_hours") or []
        hours_summary = " ".join(
            f"{h.get('day', '')} {h.get('open_time', '')}-{h.get('close_time', '')}"
            for h in hours if isinstance(h, dict) and h.get("is_open")
        )[:200]
        text = " ".join(filter(None, [
            org.get("legal_name"), org.get("display_name"), org.get("slug"),
            org.get("sms_code"), org.get("org_type"), desc[:300],
            org.get("support_email"), org.get("support_phone"), org.get("website_url"),
            org.get("country_code"), industries_text,
            vision[:200], mission[:200], objectives[:200], func_text,
            faq_text, leadership_text, hours_summary,
        ]))
        payload = {
            "org_id":               org_id,
            "legal_name":           org.get("legal_name", ""),
            "display_name":         org.get("display_name", ""),
            "slug":                 org.get("slug", ""),
            "sms_code":             org.get("sms_code", ""),
            "org_type":             org.get("org_type", ""),
            "country_code":         org.get("country_code", ""),
            "status":               org.get("status", ""),
            "description":          desc[:500],
            "support_email":        org.get("support_email", ""),
            "support_phone":        org.get("support_phone", ""),
            "website_url":          org.get("website_url", ""),
            "is_verified":          bool(org.get("is_verified", False)),
            "timezone":             org.get("timezone", ""),
            "vision":               vision[:1000],
            "mission":              mission[:1000],
            "objectives":           objectives[:1000],
            "functionalities":      functionalities[:50],
            "global_policy":        (org.get("global_policy", "") or "")[:500],
            "terms_of_use":         (org.get("terms_of_use", "") or "")[:500],
            "privacy_policy":       (org.get("privacy_policy", "") or "")[:500],
            "faqs":                 faqs[:20],
            "industries":           industries[:10],
            "feedback_form_fields": (org.get("feedback_form_fields") or [])[:50],
            "operating_hours":      hours[:7],
            "leadership":           leadership[:20],
        }
        return self.index_entity(org_id, settings.QDRANT_COLLECTION_ORGS, text, payload)

    def index_branch(self, branch_id: str, branch: dict) -> bool:
        desc = branch.get("description", "") or ""
        text = " ".join(filter(None, [
            branch.get("name"), branch.get("code"), branch.get("branch_type"),
            desc[:200], branch.get("city"), branch.get("region"), branch.get("suburb"),
            branch.get("address") or branch.get("display_name"),
            branch.get("phone"), branch.get("email"), branch.get("country"),
        ]))
        payload = {
            "branch_id":    branch_id,
            "org_id":       branch.get("org_id", ""),
            "name":         branch.get("name", ""),
            "code":         branch.get("code", ""),
            "branch_type":  branch.get("branch_type", ""),
            "status":       branch.get("status", ""),
            "latitude":     branch.get("latitude"),
            "longitude":    branch.get("longitude"),
            "city":         branch.get("city", ""),
            "region":       branch.get("region", ""),
            "suburb":       branch.get("suburb", ""),
            "country":      branch.get("country", ""),
            "address":      branch.get("address") or branch.get("display_name", ""),
            "phone":        branch.get("phone", ""),
            "email":        branch.get("email", ""),
            "description":  desc[:300],
        }
        return self.index_entity(branch_id, settings.QDRANT_COLLECTION_BRANCHES, text, payload)

    def index_department(self, dept_id: str, dept: dict) -> bool:
        desc = dept.get("description", "") or ""
        text = " ".join(filter(None, [
            dept.get("name"), dept.get("code"), desc[:300],
        ]))
        payload = {
            "dept_id":     dept_id,
            "org_id":      dept.get("org_id", ""),
            "branch_id":   dept.get("branch_id", ""),
            "name":        dept.get("name", ""),
            "code":        dept.get("code", ""),
            "description": desc[:500],
            "is_active":   bool(dept.get("is_active", True)),
        }
        return self.index_entity(dept_id, settings.QDRANT_COLLECTION_DEPARTMENTS, text, payload)

    def index_service(self, service_id: str, service: dict) -> bool:
        tags      = service.get("tags")
        tags_text = " ".join(tags) if isinstance(tags, list) else (tags or "")
        desc      = service.get("description") or service.get("summary", "") or ""

        locations = service.get("locations") or []
        loc_parts = []
        for loc in locations:
            if isinstance(loc, dict):
                for field in ("operating_hours", "virtual_platform", "notes"):
                    val = loc.get(field, "")
                    if val:
                        loc_parts.append(str(val)[:100])
        locations_text = " ".join(loc_parts)[:300]

        personnel     = service.get("personnel") or []
        personnel_text = " ".join(
            f"{p.get('personnel_title', '')} {p.get('personnel_role', '')}"
            for p in personnel if isinstance(p, dict)
        )[:200]

        faqs     = service.get("faqs") or []
        faq_text = " ".join(
            f"{f.get('question', '')} {f.get('answer', '')}"
            for f in faqs if isinstance(f, dict)
        )[:400]

        text = " ".join(filter(None, [
            service.get("title"), service.get("slug"), service.get("category"),
            service.get("subcategory"), tags_text, desc[:400],
            service.get("delivery_mode"), service.get("product_format"),
            service.get("service_type"),
            locations_text, personnel_text, faq_text,
        ]))
        payload = {
            "service_id":     service_id,
            "org_id":         service.get("org_id", ""),
            "branch_id":      service.get("branch_id", ""),
            "title":          service.get("title", ""),
            "slug":           service.get("slug", ""),
            "service_type":   service.get("service_type", ""),
            "status":         service.get("status", ""),
            "category":       service.get("category", ""),
            "subcategory":    service.get("subcategory", ""),
            "tags":           tags if isinstance(tags, list) else ([tags] if tags else []),
            "description":    desc[:600],
            "delivery_mode":  service.get("delivery_mode", ""),
            "product_format": service.get("product_format", ""),
            "base_price":     service.get("base_price"),
            "currency_code":  service.get("currency_code", ""),
            "is_featured":    bool(service.get("is_featured", False)),
            "locations":      locations[:10],
            "personnel":      personnel[:10],
            "faqs":           faqs[:20],
        }
        return self.index_entity(service_id, settings.QDRANT_COLLECTION_SERVICES, text, payload)

    def index_staff(self, staff_id: str, staff: dict) -> bool:
        expertise = staff.get("expertise")
        if isinstance(expertise, list):
            expertise_text = " ".join(str(e) for e in expertise)
        elif isinstance(expertise, dict):
            expertise_text = " ".join(str(v) for v in expertise.values())
        else:
            expertise_text = str(expertise) if expertise else ""
        text = " ".join(filter(None, [
            staff.get("first_name"), staff.get("last_name"), staff.get("display_name"),
            staff.get("staff_code"), staff.get("position"), staff.get("department"),
            staff.get("branch_name"), staff.get("employment_type"), expertise_text[:200],
        ]))
        payload = {
            "staff_id":        staff_id,
            "org_id":          staff.get("org_id", ""),
            "branch_id":       staff.get("branch_id", ""),
            "first_name":      staff.get("first_name", ""),
            "last_name":       staff.get("last_name", ""),
            "display_name":    staff.get("display_name", ""),
            "staff_code":      staff.get("staff_code", ""),
            "position":        staff.get("position", ""),
            "department":      staff.get("department", ""),
            "branch_name":     staff.get("branch_name", ""),
            "employment_type": staff.get("employment_type", ""),
            "is_verified":     bool(staff.get("is_verified", False)),
            "phone":           staff.get("phone", ""),
            "email":           staff.get("email", ""),
            "org_name":        staff.get("org_name", ""),
        }
        return self.index_entity(staff_id, settings.QDRANT_COLLECTION_STAFF, text, payload)

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
            pid     = p.get("project_id", "")
            sector  = p.get("sector", "")
            category = p.get("category", "")
            region  = p.get("region", "")
            lga     = p.get("primary_lga", "")
            wards   = ", ".join(p.get("wards", []) if isinstance(p.get("wards"), list) else [])
            stage   = p.get("active_stage_name", "")
            status  = p.get("status", "")
            desc    = p.get("description", "")
            obj     = p.get("objectives", "")
            loc     = p.get("location_description", "")
            funding = p.get("funding_source", "")
            org     = p.get("org_display_name", "")
            code    = p.get("code", "")

            line = f"- PROJECT: {name}"
            if code:
                line += f" ({code})"
            line += f" | ID: {pid}"
            if org:
                line += f" | Org: {org}"
            if sector:
                line += f" | Sector: {sector}"
            if category:
                line += f" | Category: {category}"
            if region:
                line += f" | Region: {region}"
            if lga:
                line += f" | LGA: {lga}"
            if wards:
                line += f" | Wards: {wards}"
            if loc:
                line += f" | Location: {loc}"
            if stage:
                line += f" | Stage: {stage}"
            if status:
                line += f" | Status: {status}"
            if funding:
                line += f" | Funding: {funding}"
            if desc:
                line += f"\n  Description: {desc[:200]}"
            if obj:
                line += f"\n  Objectives: {obj[:200]}"
            lines.append(line)
        return "\n".join(lines)


# Global singleton
_rag: Optional[RAGService] = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
