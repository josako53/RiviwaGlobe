"""
services/classification_service.py — Automatic feedback enrichment.

Called by the Kafka consumer whenever feedback.submitted is received.
Uses Ollama (local LLM) + Qdrant RAG to:
  1. Identify the project from description + location (if project_id is missing)
  2. Classify the category (if category_def_id is missing)

Then calls feedback_service PATCH /feedback/{id}/ai-enrich to persist the results.
"""
from __future__ import annotations
import json
import uuid
from typing import Optional, Tuple
import httpx
import structlog
from core.config import settings
from services.ollama_service import get_ollama
from services.rag_service import get_rag

log = structlog.get_logger(__name__)

_INTERNAL_HEADERS = {
    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}

# All known category slugs (must match feedback_service system categories)
_CATEGORY_SLUGS = [
    "compensation", "resettlement", "land-acquisition", "construction-impact",
    "traffic", "worker-rights", "safety-hazard", "environmental", "engagement",
    "design-issue", "project-delay", "corruption", "communication", "accessibility",
    "design", "process", "community-benefit", "employment",
    "quality", "timeliness", "staff-conduct", "community-impact", "responsiveness",
    "safety", "other",
]

_CLASSIFY_PROMPT = """Classify this GRM feedback. Reply with JSON only.

Type: {feedback_type}
Description: {description}
LGA: {lga} Ward: {ward} Location: {location}

Category options: {category_list}

Known projects:
{project_context}

JSON response (no markdown):
{{"category_slug":"<slug>","category_confidence":0.0,"project_id":"<UUID or null>","project_confidence":0.0}}"""


class ClassificationService:
    """
    Classifies a feedback record using Ollama and RAG.
    Called asynchronously when feedback.submitted Kafka events are received.
    """

    async def classify_and_enrich(self, feedback_data: dict) -> bool:
        """
        Main entry point. Returns True if any enrichment was applied.

        feedback_data: the full feedback dict from GET /feedback/{id}
        Expected keys: id, project_id, category_def_id, feedback_type,
                       description, issue_location_description,
                       issue_region, issue_lga, issue_ward
        """
        feedback_id = feedback_data.get("id")
        if not feedback_id:
            return False

        project_id      = feedback_data.get("project_id")
        category_def_id = feedback_data.get("category_def_id")

        needs_project  = not project_id
        needs_category = not category_def_id

        if not needs_project and not needs_category:
            log.debug("classification.skip", feedback_id=feedback_id,
                      reason="project_id and category_def_id already set")
            return False

        # Run Ollama classification
        result = await self._run_ollama_classification(feedback_data)
        if not result:
            return False

        # Resolve category_def_id from slug
        enrichment: dict = {}
        if needs_category and result.get("category_slug"):
            cat_def_id = await self._resolve_category_def_id(
                result["category_slug"],
                feedback_data.get("project_id"),
            )
            if cat_def_id:
                enrichment["category_def_id"] = str(cat_def_id)

        # Use RAG if project still missing after Ollama's suggestion
        if needs_project:
            project_uuid = await self._resolve_project_id(
                ollama_suggestion=result.get("project_id"),
                feedback_data=feedback_data,
            )
            if project_uuid:
                enrichment["project_id"] = str(project_uuid)

        if not enrichment:
            return False

        # Build informative note for the action log
        note_parts = ["Auto-enriched by AI service (Ollama):"]
        if "project_id" in enrichment:
            note_parts.append(f"project_id={enrichment['project_id']}")
        if "category_def_id" in enrichment:
            note_parts.append(f"category_def_id={enrichment['category_def_id']} (slug={result.get('category_slug')})")
        if result.get("reasoning"):
            note_parts.append(f"Reasoning: {result['reasoning']}")
        enrichment["note"] = " | ".join(note_parts)

        return await self._call_enrich_endpoint(feedback_id, enrichment)

    async def _run_ollama_classification(self, feedback_data: dict) -> Optional[dict]:
        """Call Ollama to classify the feedback. Returns parsed JSON or None."""
        # Build project context via RAG
        query_parts = []
        for field in ("issue_location_description", "issue_lga", "issue_ward", "issue_region", "description"):
            val = feedback_data.get(field, "")
            if val:
                query_parts.append(str(val)[:100])
        query = " ".join(query_parts)

        project_context = "No active projects in knowledge base."
        if query:
            results = get_rag().search_projects(query, top_k=5, score_threshold=0.30)
            if results:
                lines = []
                for pid, score, payload in results:
                    name = payload.get("name", "Unknown")
                    region = payload.get("region", "")
                    lga = payload.get("primary_lga", "")
                    lines.append(f"- ID: {pid} | {name} | {region} | {lga} (relevance: {score:.2f})")
                project_context = "\n".join(lines)

        prompt = _CLASSIFY_PROMPT.format(
            category_list=", ".join(_CATEGORY_SLUGS),
            feedback_type=feedback_data.get("feedback_type", "grievance"),
            description=(feedback_data.get("description") or "")[:500],
            location=feedback_data.get("issue_location_description") or "",
            region=feedback_data.get("issue_region") or "",
            lga=feedback_data.get("issue_lga") or "",
            ward=feedback_data.get("issue_ward") or "",
            project_context=project_context,
        )

        ollama = get_ollama()
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,  # low temp for classification
                "num_predict": 200,  # short JSON response only — cap tokens to avoid OOM
                "num_ctx": 1024,     # reduce context window → smaller KV cache → less RAM
            },
        }

        # Use a short timeout for pre-submit classification — if Ollama is slow/busy,
        # fail fast and fall through to the candidate-projects picker instead of
        # making the Consumer wait 60 seconds.
        _classify_timeout = min(15, settings.OLLAMA_TIMEOUT_SECS)
        try:
            async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL,
                                         timeout=_classify_timeout) as client:
                r = await client.post("/api/chat", json=payload)
                r.raise_for_status()
                content = r.json().get("message", {}).get("content", "{}")
                # Strip markdown code fences if model adds them
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[-2] if "```" in content[3:] else content[3:]
                    content = content.strip()
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract first JSON object
                    import re as _re
                    m = _re.search(r'\{.*\}', content, _re.DOTALL)
                    parsed = json.loads(m.group()) if m else {}
                # Validate category slug
                if parsed.get("category_slug") not in _CATEGORY_SLUGS:
                    parsed["category_slug"] = "other"
                log.info("classification.ollama_result",
                         feedback_id=feedback_data.get("id"),
                         category=parsed.get("category_slug"),
                         cat_confidence=parsed.get("category_confidence"),
                         project_id=parsed.get("project_id"),
                         proj_confidence=parsed.get("project_confidence"))
                return parsed
        except Exception as exc:
            log.error("classification.ollama_failed",
                      feedback_id=feedback_data.get("id"), error=str(exc))
            return None

    async def _resolve_category_def_id(
        self, slug: str, project_id: Optional[str]
    ) -> Optional[uuid.UUID]:
        """Look up category_def_id by slug from feedback_service."""
        params: dict = {"status": "active", "limit": 200}
        if project_id:
            params["project_id"] = project_id

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/categories",
                    params=params,
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code != 200:
                    return None
                items = r.json().get("items", [])
                for cat in items:
                    if cat.get("slug") == slug:
                        return uuid.UUID(cat["id"])
                # Also try global (project_id=None) categories
                if project_id:
                    r2 = await client.get(
                        f"{settings.FEEDBACK_SERVICE_URL}/api/v1/categories",
                        params={"status": "active", "limit": 200},
                        headers=_INTERNAL_HEADERS,
                    )
                    if r2.status_code == 200:
                        for cat in r2.json().get("items", []):
                            if cat.get("slug") == slug:
                                return uuid.UUID(cat["id"])
                return None
        except Exception as exc:
            log.warning("classification.category_lookup_failed", slug=slug, error=str(exc))
            return None

    async def _resolve_project_id(
        self, ollama_suggestion: Optional[str], feedback_data: dict
    ) -> Optional[uuid.UUID]:
        """
        Resolve project_id using Qdrant semantic search as the authoritative source.
        Ollama's raw UUID suggestion is NEVER trusted directly — it hallucinates.
        Only return a project_id when Qdrant finds a confident match (score >= 0.55).
        """
        query_parts = []
        for field in ("issue_location_description", "issue_lga", "issue_ward", "issue_region", "description"):
            val = feedback_data.get(field, "")
            if val:
                query_parts.append(str(val)[:100])
        if not query_parts:
            return None

        results = get_rag().search_projects(" ".join(query_parts), top_k=3, score_threshold=0.55)
        if not results:
            return None

        # If Ollama also suggested a project_id, prefer that UUID if it appears in results
        if ollama_suggestion:
            try:
                ollama_uuid = str(uuid.UUID(str(ollama_suggestion)))
                for pid, score, _ in results:
                    if pid == ollama_uuid:
                        log.info("classification.project_confirmed_by_qdrant",
                                 feedback_id=feedback_data.get("id"),
                                 project_id=pid, score=score)
                        return uuid.UUID(pid)
            except (ValueError, AttributeError):
                pass

        # Use top Qdrant result
        project_id_str, score, _ = results[0]
        log.info("classification.project_from_rag",
                 feedback_id=feedback_data.get("id"),
                 project_id=project_id_str, score=score)
        return uuid.UUID(project_id_str)

    async def classify_new_feedback(
        self,
        feedback_type: str,
        description: str,
        issue_location_description: Optional[str] = None,
        issue_lga: Optional[str] = None,
        issue_ward: Optional[str] = None,
        issue_region: Optional[str] = None,
        project_id_hint: Optional[str] = None,
    ) -> dict:
        """
        Classify a feedback record BEFORE it is created in the DB.
        Called synchronously by feedback_service during Consumer submission.

        Returns a dict with:
          - project_id (str UUID or None)
          - project_name (str or None)
          - category_slug (str)
          - category_def_id (str UUID or None)
          - confidence (float)
          - classified (bool) — True if at least one field was determined
        """
        feedback_data = {
            "feedback_type":             feedback_type,
            "description":               description,
            "issue_location_description": issue_location_description or "",
            "issue_lga":                 issue_lga or "",
            "issue_ward":                issue_ward or "",
            "issue_region":              issue_region or "",
        }

        result = await self._run_ollama_classification(feedback_data)

        out: dict = {
            "project_id":      None,
            "project_name":    None,
            "category_slug":   "other",
            "category_def_id": None,
            "confidence":      0.0,
            "classified":      False,
        }

        if not result:
            return out

        out["confidence"]    = float(result.get("category_confidence", 0.0))
        out["category_slug"] = result.get("category_slug", "other")

        # ── Resolve project_id ────────────────────────────────────────────────
        # Prefer: hint (Consumer pre-selected) > Ollama suggestion > Qdrant search
        resolved_project_id: Optional[uuid.UUID] = None
        if project_id_hint:
            try:
                resolved_project_id = uuid.UUID(str(project_id_hint))
            except (ValueError, AttributeError):
                pass

        if not resolved_project_id:
            resolved_project_id = await self._resolve_project_id(
                ollama_suggestion=result.get("project_id"),
                feedback_data=feedback_data,
            )

        if resolved_project_id:
            out["project_id"] = str(resolved_project_id)
            # Try to get the project name from Qdrant payload
            rag_results = get_rag().search_projects(
                f"{issue_lga or ''} {issue_ward or ''} {issue_location_description or ''}".strip(),
                top_k=1, score_threshold=0.0,
            )
            for pid, _, payload in rag_results:
                if pid == str(resolved_project_id):
                    out["project_name"] = payload.get("name")
                    break
            out["classified"] = True

        # ── Resolve category_def_id ───────────────────────────────────────────
        cat_def_id = await self._resolve_category_def_id(
            out["category_slug"],
            out["project_id"],
        )
        if cat_def_id:
            out["category_def_id"] = str(cat_def_id)
            out["classified"] = True

        log.info(
            "classification.new_feedback_classified",
            feedback_type=feedback_type,
            project_id=out["project_id"],
            category_slug=out["category_slug"],
            confidence=out["confidence"],
        )
        return out

    async def _call_enrich_endpoint(self, feedback_id: str, enrichment: dict) -> bool:
        """Call feedback_service PATCH /feedback/{id}/ai-enrich."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.patch(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback/{feedback_id}/ai-enrich",
                    json=enrichment,
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    data = r.json()
                    log.info("classification.enriched",
                             feedback_id=feedback_id, enriched=data.get("enriched"))
                    return data.get("enriched", False)
                log.warning("classification.enrich_failed",
                            feedback_id=feedback_id,
                            status=r.status_code, body=r.text[:200])
                return False
        except Exception as exc:
            log.error("classification.enrich_error", feedback_id=feedback_id, error=str(exc))
            return False
