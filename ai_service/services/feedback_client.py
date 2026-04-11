"""services/feedback_client.py — Internal HTTP client to feedback_service."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional
import httpx
import structlog
from core.config import settings
from core.exceptions import FeedbackSubmissionError

log = structlog.get_logger(__name__)

_INTERNAL_HEADERS = {
    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}


class FeedbackClient:
    """
    Submits feedback to feedback_service via internal HTTP.
    Maps the extracted conversation data to the feedback_service API schema.
    """

    async def submit_staff(self, data: dict) -> dict:
        """
        Submit feedback as staff (POST /api/v1/feedback).
        Used for AI-collected feedback submitted on behalf of a PAP.
        """
        payload = self._build_staff_payload(data)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback",
                    json=payload,
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code in (200, 201):
                    return r.json()
                log.error(
                    "feedback_client.submit_failed",
                    status=r.status_code,
                    body=r.text[:300],
                )
                raise FeedbackSubmissionError(
                    f"feedback_service returned {r.status_code}: {r.text[:200]}"
                )
        except FeedbackSubmissionError:
            raise
        except Exception as exc:
            log.error("feedback_client.submit_error", error=str(exc))
            raise FeedbackSubmissionError(str(exc))

    async def get_feedback_by_ref(self, unique_ref: str) -> Optional[dict]:
        """
        Look up feedback status by reference number (e.g. GRV-2025-0042).
        Uses the internal endpoint that accepts X-Service-Key without JWT.
        """
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback/by-ref/{unique_ref}",
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    return r.json()
                return None
        except Exception as exc:
            log.warning("feedback_client.get_ref_failed", ref=unique_ref, error=str(exc))
            return None

    def _build_staff_payload(self, data: dict) -> dict:
        """
        Convert extracted conversation data → feedback_service staff submission schema.
        Handles: feedback_type, description, location, category, submitter info.
        """
        # Normalise feedback_type
        raw_type = (data.get("feedback_type") or "grievance").lower()
        if raw_type not in ("grievance", "suggestion", "applause"):
            raw_type = "grievance"

        # Normalise category
        category_map = {
            "compensation": "compensation", "resettlement": "resettlement",
            "land-acquisition": "land_acquisition", "construction-impact": "construction_impact",
            "traffic": "traffic", "worker-rights": "worker_rights",
            "safety-hazard": "safety_hazard", "environmental": "environmental_impact",
            "engagement": "engagement", "design-issue": "design_issue",
            "project-delay": "project_delay", "corruption": "corruption",
            "communication": "communication", "accessibility": "accessibility",
            "design": "design", "process": "process",
            "community-benefit": "community_benefit", "employment": "employment",
            "quality": "quality", "timeliness": "timeliness",
            "staff-conduct": "staff_conduct", "community-impact": "community_impact",
            "responsiveness": "responsiveness", "safety": "safety",
            "other": "other",
        }
        cat_slug = data.get("category_slug") or "other"
        category = category_map.get(cat_slug, "other")

        payload: Dict[str, Any] = {
            "project_id": str(data["project_id"]) if data.get("project_id") else None,
            "feedback_type": raw_type,
            "category": category,
            "submission_method": "ai_conversation",
            "subject": data.get("subject") or _generate_subject(data),
            "description": data.get("description", ""),
            "is_anonymous": data.get("is_anonymous", False),
            "channel": self._map_channel(data.get("channel", "other")),
        }

        # Submitter identity
        if not payload["is_anonymous"]:
            if data.get("submitter_name"):
                payload["submitter_name"] = data["submitter_name"]
            if data.get("phone_number"):
                payload["submitter_phone"] = data["phone_number"]
            if data.get("user_id"):
                payload["submitted_by_user_id"] = str(data["user_id"])

        # Location
        if data.get("issue_location_description"):
            payload["issue_location_description"] = data["issue_location_description"]
        if data.get("ward"):
            payload["issue_ward"] = data["ward"]
        if data.get("lga"):
            payload["issue_lga"] = data["lga"]
        if data.get("region"):
            payload["issue_region"] = data["region"]
        if data.get("district"):
            payload["issue_district"] = data["district"]

        # Incident date
        if data.get("date_of_incident"):
            payload["date_of_incident"] = data["date_of_incident"]

        # Media attachments (WhatsApp images as proof)
        if data.get("media_urls"):
            payload["media_urls"] = data["media_urls"]

        return payload

    @staticmethod
    def _map_channel(channel: str) -> str:
        mapping = {
            "sms": "sms", "whatsapp": "whatsapp",
            "phone_call": "phone_call", "web": "web_portal",
            "mobile": "mobile_app",
        }
        return mapping.get(channel.lower(), "other")


def _generate_subject(data: dict) -> str:
    """Auto-generate a subject line from description if not provided."""
    desc = data.get("description", "")
    ft   = data.get("feedback_type", "feedback").capitalize()
    if desc:
        # Take first sentence or first 80 chars
        first = desc.split(".")[0].strip()
        return f"{ft}: {first[:80]}"
    return f"{ft} submitted via AI channel"


async def submit_multiple_feedback(
    client: FeedbackClient, feedback_items: List[dict], common_data: dict
) -> List[dict]:
    """
    Submit multiple feedback records when a PAP raises multiple issues in one conversation.
    Returns list of {feedback_id, unique_ref, feedback_type}.
    """
    results = []
    for item in feedback_items:
        merged = {**common_data, **item}
        try:
            resp = await client.submit_staff(merged)
            results.append({
                "feedback_id": str(resp.get("id", "")),
                "unique_ref": resp.get("unique_ref", ""),
                "feedback_type": item.get("feedback_type", "grievance"),
            })
        except FeedbackSubmissionError as exc:
            log.error("feedback_client.multi_submit_item_failed", error=str(exc))
    return results
