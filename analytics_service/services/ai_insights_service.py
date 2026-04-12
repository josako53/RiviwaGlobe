"""
services/ai_insights_service.py
────────────────────────────────────────────────────────────────────────────
AI-powered natural language insights using Groq (llama-3.3-70b-versatile).
Sends analytics context data along with the user question to Groq and
returns a natural language answer.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import structlog

from core.config import settings
from core.exceptions import AIInsightError

log = structlog.get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are Riviwa Analytics Assistant, an expert in Grievance and Feedback Management (GRM) systems.
You analyse real-time and pre-computed analytics data from the Riviwa platform and provide
clear, actionable insights to GRM officers and project managers.

Riviwa is used in development/infrastructure projects to capture grievances, suggestions,
and applause from Project Affected Persons (PAPs). Your role is to interpret the analytics
data provided in the user's message, identify patterns, risks, and opportunities, and
recommend concrete actions.

Guidelines:
- Be concise but thorough. Use bullet points for recommendations.
- Prioritise critical and high-priority items.
- When SLA compliance is low, immediately flag the risk and suggest escalation paths.
- When hotspots are detected, recommend field investigation.
- Translate numbers into plain language for non-technical users.
- If the context data is empty or insufficient, say so honestly.
- Do NOT invent data not provided in the context.
- Always end your answer with a "Next Actions" section with 2-3 prioritised actions.
""".strip()


class AIInsightsService:
    """Sends analytics context + user question to Groq, returns an answer string."""

    def __init__(self) -> None:
        self._base_url = settings.GROQ_BASE_URL.rstrip("/")
        self._api_key = settings.GROQ_API_KEY
        self._model = settings.GROQ_MODEL

    async def ask(self, question: str, context_data: Dict[str, Any]) -> str:
        """
        Send question + analytics context to Groq, return answer.

        Args:
            question: The natural language question from the user.
            context_data: Dict of relevant metrics (unresolved_count, overdue_count,
                          top_category, avg_resolution_hours, hotspots, etc.)

        Returns:
            A natural language answer string from Groq.
        """
        if not self._api_key:
            log.warning("analytics.ai_insights.no_api_key")
            raise AIInsightError(
                message="AI insights are not configured. GROQ_API_KEY is not set."
            )

        context_json = json.dumps(context_data, indent=2, default=str)
        user_message = (
            f"Analytics context data (JSON):\n```json\n{context_json}\n```\n\n"
            f"Question: {question}"
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        log.info(
            "analytics.ai_insights.request",
            model=self._model,
            context_keys=list(context_data.keys()),
            question_length=len(question),
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            log.error("analytics.ai_insights.timeout")
            raise AIInsightError(message="AI insights request timed out. Please try again.")
        except httpx.HTTPStatusError as exc:
            log.error(
                "analytics.ai_insights.http_error",
                status_code=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise AIInsightError(
                message=f"AI insights service returned an error ({exc.response.status_code})."
            )
        except Exception as exc:
            log.error("analytics.ai_insights.unexpected_error", error=str(exc))
            raise AIInsightError(message="An unexpected error occurred while fetching AI insights.")

        try:
            answer = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            log.error("analytics.ai_insights.parse_error", data=str(data)[:300], error=str(exc))
            raise AIInsightError(message="Failed to parse AI insights response.")

        log.info(
            "analytics.ai_insights.response",
            model=self._model,
            answer_length=len(answer),
        )
        return answer

    @property
    def model_name(self) -> str:
        return self._model


# Singleton instance
ai_insights_service = AIInsightsService()
