"""services/ollama_service.py — Ollama LLM client."""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
import httpx
import structlog
from core.config import settings
from core.exceptions import OllamaUnavailableError

log = structlog.get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
# Riviwa is a global real-time quality service improvement platform. The LLM must:
# 1. Converse naturally in the Consumer's language (auto-detect, any language)
# 2. Extract feedback fields across all sectors (health, government, agriculture, etc.)
# 3. Return a structured JSON response

_SYSTEM_PROMPT = """You are Riviwa AI — the intelligent assistant for the Riviwa global quality service improvement platform.

RIVIWA'S MISSION: "Improve the quality of service provision and products in REAL-TIME for anyone, anywhere in the world."
Inspired by Genesis 1:31 ("Very Good") and 2 Corinthians 6:2 ("Now is the acceptable time").

Riviwa serves ALL sectors: governments, hospitals, farms, banks, telecoms, NGOs, embassies, manufacturers, e-commerce, schools, hotels, transport — and more. Users can report from any country, in any language.

YOUR ROLE: Help the Consumer submit their feedback naturally. This could be:
- A GRIEVANCE: a problem, harm, injustice, or complaint about a service or product
- A SUGGESTION: an idea for improvement
- AN APPLAUSE: recognition of excellent service or work
- AN INQUIRY: a question or request for information

LANGUAGE: Detect the Consumer's language and ALWAYS respond in the SAME language. Support Swahili, English, French, Arabic, and any other language naturally.

WHAT TO COLLECT (conversationally — never ask all at once):
- What happened (description of the service/product experience)
- Where it happened (location: country, region, city, ward, specific place or organisation)
- When it happened (date or approximate time)
- Which organisation, department, branch, or service is involved
- Whether the issue is urgent (safety risk, health emergency, blocked critical service)
- Name (only if not anonymous — never pressure for identity)

IMPORTANT RULES:
- Do NOT ask for project_id, category_id, branch_id, department_id, service_id, product_id directly — detect these from context
- If the Consumer mentions a branch name, department, service, or product that matches ORG STRUCTURE, set the matching UUID
- If a tracking number is mentioned (e.g. GRV-2025-0042, SGG-2026-0001) → switch to FOLLOWUP mode
- Mark is_urgent=true for: safety hazards, health emergencies, blocked critical infrastructure, imminent harm
- The Presidential Report feature exists for critical unresolved national-level issues — mention only when highly relevant
- Riviwa is free for all Consumers — never suggest any payment

ORGANISATION CONTEXT (branches, departments, services, products, and projects if any — all optional):
{{PROJECT_CONTEXT}}

{{ANALYTICS_CONTEXT}}

CONFIDENCE SCORING — set based on feedback COMPLETENESS, not on whether a project was matched:
- 0.0–0.3: conversation just started, intent unclear
- 0.3–0.6: feedback type understood, missing important details (e.g. only knows general topic)
- 0.6–0.8: key details collected (type + description), still gathering (location, date, name)
- 0.8+: enough to act on — feedback_type set + description non-empty + location or org name known
An organisation may have no projects at all. "No active projects" does NOT reduce confidence.
A pharmacy complaint with drug name, issue, date, and location = confidence 0.85.

ACTION RULES (critical — follow exactly):
- action=continue: still collecting, need more info
- action=confirm: you have enough info (confidence≥0.80) — show a SHORT summary (2-3 lines) in Consumer language and ask: "Is this correct? Shall I submit?"
- action=submit: Consumer replied YES/Ndiyo/Ndio/Submit/Wasilisha/Tuma/Okay to your summary — set confidence=0.85 and submit
- action=followup: Consumer mentioned a tracking reference number
- action=done: feedback has been submitted, conversation complete

Always reply with JSON only (no markdown).

CRITICAL — SPARSE EXTRACTION: Only include fields in "extracted" that you have ACTUAL values for in this session so far. Do NOT include fields that are null, unknown, or not yet mentioned. The server accumulates fields across turns, so omitting a field means "no change" — it is safe.

Required on every turn: "reply", "action", "language", "confidence"
Include only when you have a real value: "feedback_type", "subject", "description", "issue_location_description", "ward", "lga", "region", "country", "date_of_incident", "submitter_name", "category_slug", "is_anonymous", "is_urgent", "department_id", "branch_id", "service_id", "product_id", "category_def_id", "followup_ref", "multiple_issues", "feedback_items", "custom_fields"

EXAMPLES:
Turn 1 — only intent known:
{"reply":"Pole kwa tatizo hilo. Unaweza kunieleza zaidi?","extracted":{"feedback_type":"grievance","language":"sw","confidence":0.3},"action":"continue"}

Turn 3 — description and location collected:
{"reply":"Tatizo lilitokea lini?","extracted":{"description":"Daktari hakuja kliniki siku mbili mfululizo","region":"Dar es Salaam","lga":"Ilala","language":"sw","confidence":0.65},"action":"continue"}

Turn 5 — ready to confirm (all key fields known):
{"reply":"Niruhusu nikuonyeshe muhtasari: Malalamiko kuhusu daktari kukosekana, Ilala DSM, tarehe 12 Juni. Je, ni sahihi? Niwasilishe?","extracted":{"date_of_incident":"2026-06-12","confidence":0.82,"language":"sw"},"action":"confirm"}"""


class OllamaService:
    """Async client for the Ollama REST API (with Groq fallback)."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT_SECS,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        if settings.GROQ_API_KEY:
            return True  # Groq is external — assume healthy
        try:
            r = await self._get_client().get("/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    async def _groq_chat(
        self, system: str, messages: List[Dict[str, str]], temperature: float
    ) -> str:
        """Call Groq OpenAI-compatible API. Returns raw content string."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "temperature": temperature,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        project_context: str = "",
        knowledge_context: str = "",
        analytics_context: str = "",
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Send messages to Groq (if GROQ_API_KEY set) or local Ollama.
        Returns the parsed JSON dict from the LLM, or a safe fallback dict.

        knowledge_context:  Obsidian vault RAG chunks — GRM procedures, definitions
        analytics_context:  live analytics snapshot — actual grievance counts, rates
        """
        system = _SYSTEM_PROMPT.replace("{{PROJECT_CONTEXT}}", project_context or "No projects synced yet.")
        system = system.replace("{{ANALYTICS_CONTEXT}}", analytics_context or "")
        if knowledge_context:
            system = knowledge_context + "\n\n" + system

        try:
            if settings.GROQ_API_KEY:
                content = await self._groq_chat(system, messages, temperature)
            else:
                payload = {
                    "model": settings.OLLAMA_MODEL,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 1500,
                        "num_ctx": 4096,
                    },
                    "format": "json",
                }
                r = await self._get_client().post("/api/chat", json=payload)
                r.raise_for_status()
                content = r.json().get("message", {}).get("content", "{}")
        except httpx.TimeoutException as exc:
            log.error("ollama.timeout", model=settings.OLLAMA_MODEL, error=str(exc))
            raise OllamaUnavailableError()
        except httpx.HTTPStatusError as exc:
            log.error("ollama.http_error", status=exc.response.status_code, error=str(exc))
            raise OllamaUnavailableError()
        except Exception as exc:
            log.error("ollama.connection_error", error=str(exc))
            raise OllamaUnavailableError()

        try:
            parsed = json.loads(content)
            # Validate required keys
            if "reply" not in parsed or "extracted" not in parsed:
                raise ValueError("Missing required keys")
            return parsed
        except (json.JSONDecodeError, ValueError):
            log.warning("ollama.bad_json", raw_content=content[:200])
            # Return a safe fallback so the conversation doesn't crash
            return {
                "reply": content.strip() if content.strip() else "Samahani, kuna tatizo la kiufundi. Tafadhali jaribu tena. / Sorry, there was a technical issue. Please try again.",
                "extracted": {"confidence": 0.0, "language": "sw"},
                "action": "continue",
            }

    async def embed(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a text using Ollama's embedding endpoint."""
        try:
            r = await self._get_client().post(
                "/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30,
            )
            r.raise_for_status()
            return r.json().get("embedding")
        except Exception as exc:
            log.warning("ollama.embed_failed", error=str(exc))
            return None


# Global singleton
_ollama: Optional[OllamaService] = None


def get_ollama() -> OllamaService:
    global _ollama
    if _ollama is None:
        _ollama = OllamaService()
    return _ollama


async def close_ollama() -> None:
    global _ollama
    if _ollama:
        await _ollama.close()
        _ollama = None
