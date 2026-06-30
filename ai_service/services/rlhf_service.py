"""
services/rlhf_service.py — Reinforcement Learning from Human Feedback (RLHF)

Watches resolved feedback events and extracts reusable Owner Standard scenarios
to append to the appropriate KB_88 industry file for Obsidian RAG retrieval.

Eligibility rules:
  GRIEVANCE  → status resolved/closed AND resolution.grievant_satisfied = True
  SUGGESTION → status = actioned (staff marked it implemented)
  APPLAUSE   → status = closed (staff acknowledged)
  INQUIRY    → status = resolved or closed (answer provided)

Resolution classification (computed from submitted_at → resolved_at):
  real_time  → resolved in < 1 hour
  same_day   → resolved in 1–24 hours
  deferred   → resolved in > 24 hours
"""
from __future__ import annotations

import re
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

_INTERNAL_HEADERS = {
    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}

# ── Industry slug → KB_88 file mapping ────────────────────────────────────────
# Each entry: (keyword_to_match_in_slug, two_digit_num, file_suffix)
# The first keyword match wins, so more-specific entries come first.

_SLUG_MAP: list[tuple[str, str, str]] = [
    ("healthcare",           "01", "healthcare_hospital"),
    ("hospital",             "01", "healthcare_hospital"),
    ("medical",              "01", "healthcare_hospital"),
    ("health_care",          "01", "healthcare_hospital"),
    ("pharmacy",             "02", "pharmacy_pharmaceutical"),
    ("pharmaceutical",       "02", "pharmacy_pharmaceutical"),
    ("drug",                 "02", "pharmacy_pharmaceutical"),
    ("fintech",              "03", "finance_banking"),
    ("microfinance",         "03", "finance_banking"),
    ("finance",              "03", "finance_banking"),
    ("banking",              "03", "finance_banking"),
    ("bank",                 "03", "finance_banking"),
    ("reinsurance",          "04", "insurance"),
    ("insurance",            "04", "insurance"),
    ("telecom",              "05", "telecommunications"),
    ("telecommunications",   "05", "telecommunications"),
    ("mobile_network",       "05", "telecommunications"),
    ("internet_provider",    "05", "telecommunications"),
    ("electricity",          "06", "energy_utilities_water"),
    ("water_utility",        "06", "energy_utilities_water"),
    ("energy",               "06", "energy_utilities_water"),
    ("utilities",            "06", "energy_utilities_water"),
    ("utility",              "06", "energy_utilities_water"),
    ("water",                "06", "energy_utilities_water"),
    ("power",                "06", "energy_utilities_water"),
    ("civil_service",        "07", "government_public_services"),
    ("municipality",         "07", "government_public_services"),
    ("public_service",       "07", "government_public_services"),
    ("government",           "07", "government_public_services"),
    ("consulate",            "08", "embassy_immigration"),
    ("embassy",              "08", "embassy_immigration"),
    ("immigration",          "08", "embassy_immigration"),
    ("humanitarian",         "09", "ngo_development"),
    ("non_profit",           "09", "ngo_development"),
    ("nonprofit",            "09", "ngo_development"),
    ("ngo",                  "09", "ngo_development"),
    ("development",          "09", "ngo_development"),
    ("aid",                  "09", "ngo_development"),
    ("ecommerce",            "10", "retail_consumer_products"),
    ("supermarket",          "10", "retail_consumer_products"),
    ("consumer_products",    "10", "retail_consumer_products"),
    ("retail",               "10", "retail_consumer_products"),
    ("beverage",             "11", "food_consumables"),
    ("fmcg",                 "11", "food_consumables"),
    ("consumable",           "11", "food_consumables"),
    ("food",                 "11", "food_consumables"),
    ("appliance",            "12", "electronics_technology"),
    ("electronics",          "12", "electronics_technology"),
    ("hardware",             "12", "electronics_technology"),
    ("aviation",             "13", "transport_public_transit"),
    ("airline",              "13", "transport_public_transit"),
    ("transit",              "13", "transport_public_transit"),
    ("transport",            "13", "transport_public_transit"),
    ("bus",                  "13", "transport_public_transit"),
    ("rail",                 "13", "transport_public_transit"),
    ("supply_chain",         "14", "logistics_supply_chain"),
    ("courier",              "14", "logistics_supply_chain"),
    ("freight",              "14", "logistics_supply_chain"),
    ("shipping",             "14", "logistics_supply_chain"),
    ("logistics",            "14", "logistics_supply_chain"),
    ("automotive",           "15", "automobiles_motor_vehicles"),
    ("automobile",           "15", "automobiles_motor_vehicles"),
    ("vehicle",              "15", "automobiles_motor_vehicles"),
    ("motor",                "15", "automobiles_motor_vehicles"),
    ("car_dealer",           "15", "automobiles_motor_vehicles"),
    ("academic",             "16", "education_university"),
    ("university",           "16", "education_university"),
    ("college",              "16", "education_university"),
    ("education",            "16", "education_university"),
    ("school",               "16", "education_university"),
    ("professional_dev",     "17", "training_professional_development"),
    ("vocational",           "17", "training_professional_development"),
    ("training",             "17", "training_professional_development"),
    ("management_consulting","18", "business_consultancy"),
    ("consultancy",          "18", "business_consultancy"),
    ("consulting",           "18", "business_consultancy"),
    ("advisory",             "18", "business_consultancy"),
    ("solicitor",            "19", "legal_services"),
    ("lawyer",               "19", "legal_services"),
    ("legal",                "19", "legal_services"),
    ("law",                  "19", "legal_services"),
    ("engineering",          "20", "construction_real_estate_dev"),
    ("construction",         "20", "construction_real_estate_dev"),
    ("landlord",             "21", "real_estate_property"),
    ("housing",              "21", "real_estate_property"),
    ("real_estate",          "21", "real_estate_property"),
    ("property",             "21", "real_estate_property"),
    ("extractive",           "22", "mining_extractive_industries"),
    ("mining",               "22", "mining_extractive_industries"),
    ("oil",                  "22", "mining_extractive_industries"),
    ("gas",                  "22", "mining_extractive_industries"),
    ("social_protection",    "23", "social_welfare"),
    ("social_service",       "23", "social_welfare"),
    ("social_welfare",       "23", "social_welfare"),
    ("welfare",              "23", "social_welfare"),
    ("restaurant",           "24", "tourism_hospitality"),
    ("hospitality",          "24", "tourism_hospitality"),
    ("tourism",              "24", "tourism_hospitality"),
    ("hotel",                "24", "tourism_hospitality"),
    ("agribusiness",         "25", "agriculture_agribusiness"),
    ("agro",                 "25", "agriculture_agribusiness"),
    ("farming",              "25", "agriculture_agribusiness"),
    ("agriculture",          "25", "agriculture_agribusiness"),
    ("events_management",    "26", "events_entertainment"),
    ("events",               "26", "events_entertainment"),
    ("mosque",               "27", "church_religious_organizations"),
    ("religious",            "27", "church_religious_organizations"),
    ("faith",                "27", "church_religious_organizations"),
    ("church",               "27", "church_religious_organizations"),
    ("broadcasting",         "28", "media_entertainment"),
    ("newspaper",            "28", "media_entertainment"),
    ("streaming",            "28", "media_entertainment"),
    ("media",                "28", "media_entertainment"),
    ("life_coach",           "29", "personal_development_coaching"),
    ("personal_development", "29", "personal_development_coaching"),
    ("coaching",             "29", "personal_development_coaching"),
    ("saas",                 "30", "technology_software"),
    ("it_services",          "30", "technology_software"),
    ("software",             "30", "technology_software"),
    ("technology",           "30", "technology_software"),
    ("tech",                 "30", "technology_software"),
    ("factory",              "31", "manufacturing"),
    ("production",           "31", "manufacturing"),
    ("manufacturing",        "31", "manufacturing"),
    ("security_services",    "32", "security_services"),
    ("guarding",             "32", "security_services"),
    ("security",             "32", "security_services"),
    ("fitness",              "33", "health_wellness"),
    ("wellness",             "33", "health_wellness"),
    ("beauty",               "33", "health_wellness"),
    ("spa",                  "33", "health_wellness"),
    ("gym",                  "33", "health_wellness"),
]


def slug_to_kb88_filename(industry_slug: str) -> Optional[str]:
    """Map an auth_service industry slug to the KB_88 markdown filename."""
    slug = industry_slug.lower().replace("-", "_").replace(" ", "_")
    for keyword, num, suffix in _SLUG_MAP:
        if keyword in slug or slug == keyword or slug.startswith(keyword):
            return f"KB_88_{num}_owner_scenarios_{suffix}.md"
    # Reverse partial match
    for keyword, num, suffix in _SLUG_MAP:
        if slug in keyword:
            return f"KB_88_{num}_owner_scenarios_{suffix}.md"
    return None


def classify_resolution_time(submitted_at: Optional[str], resolved_at: Optional[str]) -> str:
    """Return 'real_time', 'same_day', or 'deferred' based on time delta."""
    try:
        if not submitted_at or not resolved_at:
            return "deferred"
        t0 = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        hours = (t1 - t0).total_seconds() / 3600
        if hours < 1:
            return "real_time"
        if hours <= 24:
            return "same_day"
        return "deferred"
    except Exception:
        return "deferred"


# ── RLHF Service ───────────────────────────────────────────────────────────────

class RLHFService:
    """
    Extracts reusable Owner Standard scenarios from resolved feedback
    and appends them to the appropriate KB_88 industry file.
    """

    async def process_resolved_feedback(self, feedback_id: str) -> bool:
        """
        Main entry point — called from the Kafka consumer on feedback.resolved.
        Returns True if a new scenario was written.
        """
        log.info("rlhf.processing", feedback_id=feedback_id)

        feedback = await self._fetch_feedback(feedback_id)
        if not feedback:
            return False

        if not self._is_eligible(feedback):
            log.debug("rlhf.not_eligible", feedback_id=feedback_id,
                      feedback_type=feedback.get("feedback_type"),
                      status=feedback.get("status"))
            return False

        org_id = str(feedback.get("org_id") or "")
        if not org_id or org_id == "None":
            log.warning("rlhf.no_org_id", feedback_id=feedback_id)
            return False

        industry_slug, kb88_filename = await self._resolve_industry(org_id)
        if not kb88_filename:
            log.warning("rlhf.no_industry_match", feedback_id=feedback_id,
                        org_id=org_id, industry_slug=industry_slug)
            return False

        resolution = feedback.get("resolution") or {}
        resolution_class = classify_resolution_time(
            str(feedback.get("submitted_at") or ""),
            str(resolution.get("resolved_at") or ""),
        )

        scenario = await self._extract_scenario(feedback, industry_slug, resolution_class)
        if not scenario:
            log.warning("rlhf.extraction_failed", feedback_id=feedback_id)
            return False

        if not await self._passes_quality_gate(scenario, kb88_filename):
            log.info("rlhf.quality_gate_failed", feedback_id=feedback_id)
            return False

        try:
            self._append_scenario_to_file(scenario, kb88_filename, resolution_class)
            self._reindex_single_file(kb88_filename)
            log.info("rlhf.scenario_written", feedback_id=feedback_id,
                     file=kb88_filename, pattern=scenario.get("pattern"),
                     resolution_class=resolution_class)
            return True
        except Exception as exc:
            log.error("rlhf.write_failed", feedback_id=feedback_id, error=str(exc))
            return False

    # ── Fetch feedback ─────────────────────────────────────────────────────────

    async def _fetch_feedback(self, feedback_id: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback/{feedback_id}/for-ai",
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    return r.json()
                log.warning("rlhf.fetch_failed",
                            feedback_id=feedback_id, status=r.status_code)
        except Exception as exc:
            log.error("rlhf.fetch_error", feedback_id=feedback_id, error=str(exc))
        return None

    # ── Eligibility check ─────────────────────────────────────────────────────

    def _is_eligible(self, feedback: dict) -> bool:
        fb_type = (feedback.get("feedback_type") or "").lower()
        status  = (feedback.get("status") or "").lower()

        if fb_type == "grievance":
            resolution = feedback.get("resolution") or {}
            return (
                resolution.get("grievant_satisfied") is True
                and status in ("resolved", "closed")
            )
        if fb_type == "suggestion":
            return status == "actioned"
        if fb_type == "applause":
            return status == "closed"
        if fb_type == "inquiry":
            return status in ("resolved", "closed")
        return False

    # ── Industry resolution ────────────────────────────────────────────────────

    async def _resolve_industry(self, org_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Return (industry_slug, kb88_filename) or (None, None)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/internal/orgs/{org_id}",
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code != 200:
                    log.warning("rlhf.org_fetch_failed",
                                org_id=org_id, status=r.status_code)
                    return None, None

                org        = r.json()
                industries = org.get("industries") or []

                slug: Optional[str] = None
                for ind in industries:
                    if ind.get("is_primary"):
                        slug = ind.get("slug") or ""
                        break
                if not slug and industries:
                    slug = industries[0].get("slug") or ""
                if not slug:
                    return None, None

                filename = slug_to_kb88_filename(slug)
                return slug, filename

        except Exception as exc:
            log.error("rlhf.industry_resolve_error", org_id=org_id, error=str(exc))
            return None, None

    # ── LLM extraction ─────────────────────────────────────────────────────────

    async def _extract_scenario(
        self,
        feedback: dict,
        industry_slug: str,
        resolution_class: str,
    ) -> Optional[dict]:
        """Use Groq (or Ollama fallback) to extract a structured KB_88 scenario."""
        fb_type     = feedback.get("feedback_type", "grievance")
        description = (feedback.get("description") or "").strip()
        resolution  = feedback.get("resolution") or {}
        resolution_text = (
            resolution.get("resolution_summary")
            or resolution.get("resolution_action")
            or ""
        ).strip()

        if len(description.split()) < 20:
            return None

        prompt = f"""You are extracting a real-world Owner Standard service scenario from a resolved {fb_type} in the {industry_slug} industry.

CONSUMER FEEDBACK:
{description}

RESOLUTION PROVIDED BY STAFF:
{resolution_text or "(no summary recorded)"}

RESOLUTION SPEED: {resolution_class}

Extract a reusable scenario in exactly this JSON format (no other text):
{{
  "title": "5-10 word title describing the core issue",
  "problem": "What the consumer experienced — 2-3 sentences, generalised so other orgs can learn from it",
  "staff_response": "The typical inadequate staff response to this situation (the wrong or lazy approach)",
  "owner_does": "What an excellent Owner would do — immediate, specific, real-time solution (2-3 sentences)",
  "ai_reply": "What Riviwa AI should say to a consumer facing this issue (1-2 sentences, direct and helpful)",
  "direct_to": "Who or what to direct the consumer to (specific department, person title, law, right, or contact)",
  "is_urgent": false,
  "pattern": "A",
  "category_tag": "service_failure"
}}

Pattern options (choose the most fitting):
A = Find the solution right now — never send the consumer away
B = Never dismiss the need — work with what is available
C = Know where the solution is — direct precisely when you cannot resolve directly
D = Life or safety over procedure — urgent need overrides every rule
E = Treat as you would treat your own loved one (empathy and dignity)

category_tag options: safety / billing / service_failure / staff_conduct / access / delay / quality / information / policy / other

Return ONLY the JSON object. No markdown, no explanation."""

        return await self._call_llm_json(prompt)

    async def _call_llm_json(self, prompt: str) -> Optional[dict]:
        """Call Groq if API key is set, otherwise fall back to Ollama."""
        import json

        if settings.GROQ_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    r = await client.post(
                        f"{settings.GROQ_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model":       settings.GROQ_MODEL,
                            "messages":    [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens":  700,
                        },
                    )
                    if r.status_code == 200:
                        raw = r.json()["choices"][0]["message"]["content"].strip()
                        raw = re.sub(r'^```(?:json)?\s*', '', raw)
                        raw = re.sub(r'\s*```$', '', raw)
                        return json.loads(raw)
                    log.warning("rlhf.groq_http_error", status=r.status_code)
            except Exception as exc:
                log.warning("rlhf.groq_failed", error=str(exc))

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model":   settings.OLLAMA_MODEL,
                        "prompt":  prompt,
                        "stream":  False,
                        "options": {"temperature": 0.3},
                    },
                )
                if r.status_code == 200:
                    raw = r.json().get("response", "").strip()
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                    return json.loads(raw)
        except Exception as exc:
            log.warning("rlhf.ollama_failed", error=str(exc))

        return None

    # ── Quality gate ──────────────────────────────────────────────────────────

    async def _passes_quality_gate(self, scenario: dict, kb88_filename: str) -> bool:
        """Reject scenarios that are too short or already exist in the knowledge base."""
        problem    = scenario.get("problem", "")
        owner_does = scenario.get("owner_does", "")

        if len(problem.split()) < 15 or len(owner_does.split()) < 15:
            return False

        try:
            from services.obsidian_rag_service import get_obsidian_rag
            rag     = get_obsidian_rag()
            query   = f"{scenario.get('title', '')} {problem}"
            results = rag.search(query, top_k=1)
            for _text, score, source in results:
                if source == kb88_filename and score > 0.92:
                    log.info("rlhf.duplicate_detected", score=score, source=source)
                    return False
        except Exception as exc:
            log.warning("rlhf.novelty_check_error", error=str(exc))

        return True

    # ── File write ────────────────────────────────────────────────────────────

    def _append_scenario_to_file(
        self,
        scenario: dict,
        kb88_filename: str,
        resolution_class: str,
    ) -> None:
        """Append the extracted scenario to the KB_88 markdown file."""
        vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
        file_path  = vault_path / kb88_filename

        if not file_path.exists():
            raise FileNotFoundError(f"KB88 file not found: {kb88_filename}")

        content = file_path.read_text(encoding="utf-8")

        matches    = re.findall(r'### Scenario \d+-(\d+)', content)
        next_num   = max(int(m) for m in matches) + 1 if matches else 11
        num_match  = re.match(r'KB_88_(\d+)_', kb88_filename)
        industry_n = num_match.group(1) if num_match else "XX"
        today      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        is_urgent  = scenario.get("is_urgent", False)

        new_block = (
            f"\n---\n\n"
            f"### Scenario {industry_n}-{next_num}: "
            f"{scenario.get('title', 'Auto-extracted scenario')}"
            f" *(RLHF — {today})*\n\n"
            f"**Real Basis:** Extracted from a resolved "
            f"{scenario.get('category_tag', 'service')} case on the Riviwa platform "
            f"(anonymised — resolution speed: {resolution_class}).\n\n"
            f"**The Problem:** {scenario.get('problem', '')}\n\n"
            f"**What staff would do:** "
            f"{scenario.get('staff_response', 'Follow standard procedure without proactively solving the issue.')}\n\n"
            f"**What the Owner does:** {scenario.get('owner_does', '')}\n\n"
            f"**Riviwa AI Instruction:**\n"
            f"- is_urgent: {str(is_urgent).lower()}\n"
            f"- reply: {scenario.get('ai_reply', '')}\n"
            f"- direct_to: {scenario.get('direct_to', 'the relevant department or service team')}\n"
            f"- category_tag: {scenario.get('category_tag', 'other')}\n"
            f"- pattern: {scenario.get('pattern', 'A')}\n"
            f"- resolution_class: {resolution_class}\n"
        )

        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(new_block)

        log.info("rlhf.scenario_appended",
                 file=kb88_filename, scenario_num=f"{industry_n}-{next_num}")

    # ── Qdrant re-index ───────────────────────────────────────────────────────

    def _reindex_single_file(self, kb88_filename: str) -> None:
        """Re-embed and upsert only the updated KB_88 file into Qdrant."""
        vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
        file_path  = vault_path / kb88_filename

        try:
            from services.obsidian_rag_service import (
                get_obsidian_rag,
                _get_model,
                _get_qdrant,
            )
            from qdrant_client.models import PointStruct

            rag    = get_obsidian_rag()
            model  = _get_model()
            client = _get_qdrant()

            if not model or not client:
                log.warning("rlhf.reindex_skipped", reason="model or qdrant unavailable")
                return

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            chunks  = rag._chunk_markdown(content, str(file_path))
            points  = []

            for chunk in chunks:
                if len(chunk["text"].split()) < 10:
                    continue
                vector   = model.encode(chunk["text"]).tolist()
                point_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, chunk["chunk_id"]))
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text":     chunk["text"],
                        "source":   chunk["source"],
                        "chunk_id": chunk["chunk_id"],
                        "file":     kb88_filename,
                    },
                ))

            if points:
                client.upsert(collection_name=rag.COLLECTION, points=points)
                log.info("rlhf.reindexed", file=kb88_filename, chunks=len(points))

        except Exception as exc:
            log.error("rlhf.reindex_error", file=kb88_filename, error=str(exc))


# ── Singleton ─────────────────────────────────────────────────────────────────

_rlhf_service: Optional[RLHFService] = None


def get_rlhf_service() -> RLHFService:
    global _rlhf_service
    if _rlhf_service is None:
        _rlhf_service = RLHFService()
    return _rlhf_service
