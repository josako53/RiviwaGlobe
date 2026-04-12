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
# Bilingual (Swahili + English) GRM context. The LLM must:
# 1. Converse naturally in the PAP's language
# 2. Extract feedback fields
# 3. Return a structured JSON response

_SYSTEM_PROMPT = """You are Riviwa AI, a GRM assistant for World Bank infrastructure projects in Tanzania.
Help PAPs submit grievances, suggestions, or applause in Swahili or English (match their language).

Collect naturally: description, location (ward, LGA), date, name (if not anonymous).
Do NOT ask for project_id or category — you detect these from context.
If tracking number mentioned (e.g. GRV-2025-0042) → FOLLOWUP mode.
Mark is_urgent=true for safety hazards or blocked roads.
At confidence≥0.80 show summary and ask confirmation. Then set ready_to_submit=true.

PROJECTS: {{PROJECT_CONTEXT}}

Always reply with JSON only (no markdown):
{"reply":"<response in PAP language>","extracted":{"feedback_type":"grievance|suggestion|applause|unknown","subject":"<summary>","description":"<detail>","issue_location_description":"<location>","ward":null,"lga":null,"region":null,"date_of_incident":null,"is_anonymous":false,"submitter_name":null,"category_slug":"other","language":"sw","confidence":0.0,"ready_to_submit":false,"is_followup":false,"followup_ref":null,"is_urgent":false,"multiple_issues":false,"feedback_items":[]},"action":"continue|confirm|submit|followup|done"}"""


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
                    "max_tokens": 512,
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
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Send messages to Groq (if GROQ_API_KEY set) or local Ollama.
        Returns the parsed JSON dict from the LLM, or a safe fallback dict.

        knowledge_context: optional RAG context from Obsidian vault prepended
        to the system prompt to ground answers in org-specific knowledge.
        """
        system = _SYSTEM_PROMPT.replace("{{PROJECT_CONTEXT}}", project_context or "No projects synced yet.")
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
                        "num_predict": 512,
                        "num_ctx": 2048,
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
