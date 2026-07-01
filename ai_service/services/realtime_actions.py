"""
services/realtime_actions.py — Real-time integration helpers for the AI conversation.

Each function is:
  - async (or pure where no I/O needed)
  - returns None / empty string / False on any failure — never crashes a conversation
  - uses INTERNAL_SERVICE_KEY for all service-to-service calls
  - uses httpx.AsyncClient with short timeouts

AI-1:  extract_location_from_text  — parse GPS/place name from user message
AI-2+3: get_nearest_office          — find nearest org branch, format directions
AI-4:  get_staff_contact_for_issue  — org gram lookup for relevant contact
AI-5:  get_queue_eta                — fetch estimated wait time from waiting service
AI-6:  add_to_queue                 — join a queue in the waiting service
AI-7:  notify_staff_of_grievance    — staff notification via notification service
AI-9:  build_closing_prompts        — cross-type prompting at session close
AI-10: classify_urgency             — detect urgency keywords in feedback text
AI-11: format_ref_message           — format tracking number delivery message
AI-12: schedule_followup            — schedule follow-up notification via Kafka
AI-13: detect_and_translate         — language detection + translation
AI-14: lookup_transaction           — payment/transaction lookup
AI-15: verify_product               — product authenticity check
AI-16: check_systemic_pattern       — check if complaint matches analytics hotspot
AI-17: get_org_content              — pull relevant CMS post for a topic
AI-21: notify_praised_staff         — notify praised staff + record performance flag
AI-22: synthesize_response          — format text for TTS/IVR delivery
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

_INTERNAL_HEADERS = {
    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}


# ─────────────────────────────────────────────────────────────────────────────
# AI-1: Location extraction from free text
# ─────────────────────────────────────────────────────────────────────────────

def extract_location_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract GPS coordinates or a place name from a user message.
    Returns {"gps_lat": float, "gps_lng": float} or {"location_text": str} or None.
    The caller should merge this into the conversation's extracted data so that
    the existing _resolve_entities / location_service pipeline picks it up.
    """
    if not text:
        return None

    # GPS pattern: "-6.7924, 39.2083"  or  "lat -6.79 lng 39.20"
    coord_pat = re.search(
        r'(-?\d{1,3}\.\d{2,8})\s*[,;/\s]\s*(-?\d{1,3}\.\d{2,8})',
        text,
    )
    if coord_pat:
        try:
            lat = float(coord_pat.group(1))
            lng = float(coord_pat.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return {"gps_lat": lat, "gps_lng": lng}
        except ValueError:
            pass

    # Place name patterns (English and Swahili)
    place_patterns = [
        r'\bat\s+([A-Z][a-zA-Z\s,]{3,60})',
        r'\bnear\s+([A-Z][a-zA-Z\s,]{3,60})',
        r'\bin\s+([A-Z][a-zA-Z\s,]{3,40})',
        r'\bniko\s+([A-Za-z\s]{3,60})',
        r'\bkatika\s+([A-Za-z\s]{3,60})',
        r'\bkaribu\s+na\s+([A-Za-z\s]{3,60})',
        r'\bjioni\s+ya\s+([A-Za-z\s]{3,50})',
    ]
    for pat in place_patterns:
        m = re.search(pat, text)
        if m:
            place = m.group(1).strip().rstrip(",.")
            if len(place) >= 3:
                return {"location_text": place}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-2 + AI-3: Nearest office + directions
# ─────────────────────────────────────────────────────────────────────────────

async def get_nearest_office(
    org_id: str,
    user_lat: float,
    user_lng: float,
    language: str = "en",
) -> str:
    """
    Call auth service /internal/locations/nearest and return a formatted
    directions string.  Returns "" on any failure.
    """
    if not org_id or user_lat is None or user_lng is None:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/locations/nearest",
                params={
                    "lat":       user_lat,
                    "lng":       user_lng,
                    "org_id":    org_id,
                    "radius_km": 50,
                },
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code != 200:
            log.debug("realtime.nearest_office_not_found",
                      status=r.status_code, org_id=org_id)
            return ""
        data = r.json()
    except Exception as exc:
        log.warning("realtime.nearest_office_error", error=str(exc), org_id=org_id)
        return ""

    name          = data.get("name") or data.get("branch_name") or "Branch"
    location_type = data.get("location_type") or data.get("branch_type") or "branch"
    distance      = data.get("distance_km")
    address       = data.get("address") or data.get("display_name") or ""
    directions    = data.get("directions") or ""
    dist_str      = f"{distance:.1f}km" if distance is not None else "nearby"

    if language == "sw":
        msg = (
            f"Ofisi yetu ya karibu ni {name} ({location_type}), "
            f"iko umbali wa {dist_str} kutoka kwako"
        )
        if address:
            msg += f", iko {address}"
        msg += "."
        if directions:
            msg += f" Maelekezo: {directions}"
    else:
        msg = f"The nearest {location_type} is {name}, {dist_str} from you"
        if address:
            msg += f" at {address}"
        msg += "."
        if directions:
            msg += f" Directions: {directions}"

    return msg


# ─────────────────────────────────────────────────────────────────────────────
# AI-4: Org gram lookup — relevant staff contact for an issue type
# ─────────────────────────────────────────────────────────────────────────────

# Maps issue categories to leadership title keywords
_ISSUE_CONTACT_KEYWORDS: Dict[str, List[str]] = {
    "pharmacy":    ["pharmacy", "pharmacist", "drug", "medicine", "dawa"],
    "it":          ["it", "tech", "computer", "system", "network", "teknolojia"],
    "finance":     ["finance", "billing", "payment", "invoice", "fedha", "malipo"],
    "hr":          ["hr", "human resource", "staff", "employee", "rasilimali"],
    "medical":     ["doctor", "medical", "physician", "clinical", "daktari", "kliniki"],
    "nursing":     ["nurse", "nursing", "ward", "muuguzi"],
    "maintenance": ["maintenance", "facility", "building", "matengenezo"],
    "security":    ["security", "guard", "usalama"],
    "transport":   ["transport", "ambulance", "vehicle", "usafiri", "gari"],
    "general":     ["manager", "director", "ceo", "chief", "head", "mkurugenzi"],
}


async def get_staff_contact_for_issue(
    org_id: str,
    issue_description: str,
) -> Optional[Dict[str, Any]]:
    """
    Find the most relevant staff contact for an issue using the staff_service
    internal bulk endpoint, scoring by department/position keyword match.
    Returns {name, title, phone, email} or None on failure / no staff found.
    """
    if not org_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{settings.STAFF_SERVICE_URL}/api/v1/staff/internal/staff",
                params={"limit": 100},
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception as exc:
        log.warning("realtime.staff_contact_error", error=str(exc), org_id=org_id)
        return None

    # Filter to this org and staff with contact info
    staff = [
        s for s in (data.get("items") or [])
        if str(s.get("org_id") or "") == org_id
        and (s.get("phone") or s.get("email"))
    ]
    if not staff:
        return None

    issue_lower = (issue_description or "").lower()
    best_contact = None
    best_score   = -1

    for member in staff:
        title = (member.get("position") or "").lower()
        dept  = (member.get("department") or "").lower()
        score = 0
        for keywords in _ISSUE_CONTACT_KEYWORDS.values():
            title_hit = any(kw in title or kw in dept for kw in keywords)
            issue_hit = any(kw in issue_lower for kw in keywords)
            if title_hit and issue_hit:
                score += 3
            elif title_hit:
                score += 1
        if score > best_score:
            best_score   = score
            best_contact = member

    if best_contact is None:
        best_contact = staff[0]  # fallback to first staff with contact info

    return {
        "name":  best_contact.get("display_name") or best_contact.get("first_name") or "Manager",
        "title": best_contact.get("position") or "",
        "phone": best_contact.get("phone") or "",
        "email": best_contact.get("email") or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI-5: Queue availability check (get default flow for org)
# ─────────────────────────────────────────────────────────────────────────────

async def get_queue_eta(org_id: str) -> Optional[Dict[str, Any]]:
    """
    Check whether the org has an active queue flow via the waiting service
    internal endpoint.  Returns {flow_id, flow_name} when available, or None.
    ETA is returned from add_to_queue() after joining.
    """
    if not org_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{settings.WAITING_SERVICE_URL}/api/v1/waiting/internal/{org_id}/default-flow",
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code == 200:
            data = r.json()
            if data.get("flow_id"):
                return data  # {flow_id, flow_name}
        return None
    except Exception as exc:
        log.warning("realtime.queue_eta_error", error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-6: Join queue
# ─────────────────────────────────────────────────────────────────────────────

async def add_to_queue(
    user_phone: str,
    org_id: str,
    flow_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Join the queue for the user using the waiting service.
    Requires flow_id (get from get_queue_eta first).
    Returns {ticket_number, position_in_queue, eta_minutes} or None on failure.
    """
    if not user_phone or not org_id or not flow_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{settings.WAITING_SERVICE_URL}/api/v1/waiting/join",
                json={
                    "org_id":       org_id,
                    "flow_id":      flow_id,
                    "phone_number": user_phone,
                    "channel":      "SMS",
                },
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code in (200, 201):
            return r.json()
        log.warning("realtime.add_to_queue_failed", status=r.status_code)
        return None
    except Exception as exc:
        log.warning("realtime.add_to_queue_error", error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Queue keyword detection (triggers AI-5/6 in conversation)
# ─────────────────────────────────────────────────────────────────────────────

_QUEUE_KEYWORDS = frozenset({
    "queue", "join", "waiting", "wait", "ticket", "line", "number",
    # Swahili
    "foleni", "ingia", "nambari", "ngoja", "subiri", "nambari ya kusubiri",
})


def detect_queue_keywords(text: str) -> bool:
    """Return True if text contains queue/waiting intent keywords (en + sw)."""
    if not text:
        return False
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return bool(words & _QUEUE_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# AI-7: Staff grievance notification
# ─────────────────────────────────────────────────────────────────────────────

async def notify_staff_of_grievance(
    staff_phone: str,
    staff_name: str,
    feedback_ref: str,
    subject: str,
    priority: str,
    sla_hours: int,
    org_name: str,
) -> bool:
    """
    Send a grievance alert to a staff member via the notification service
    using the grm.grievance.escalated_to_staff template.
    Returns True on success, False on failure.
    """
    if not staff_phone or not feedback_ref:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/internal/notify",
                json={
                    "notification_type": "grm.grievance.escalated_to_staff",
                    "recipient": {
                        "phone": staff_phone,
                        "name":  staff_name,
                    },
                    "channels": ["sms", "push"],
                    "variables": {
                        "staff_name":   staff_name,
                        "feedback_ref": feedback_ref,
                        "subject":      subject,
                        "priority":     priority,
                        "sla_hours":    str(sla_hours),
                        "org_name":     org_name,
                    },
                },
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code not in (200, 201, 202):
            log.warning("realtime.notify_staff_failed",
                        status=r.status_code, ref=feedback_ref)
            return False
        return True
    except Exception as exc:
        log.warning("realtime.notify_staff_error", error=str(exc))
        return False


# ─────────────────────────────────────────────────────────────────────────────
# AI-9: Cross-type closing prompts
# ─────────────────────────────────────────────────────────────────────────────

_CLOSING_PROMPTS: Dict[str, Dict[str, str]] = {
    "grievance": {
        "en": (
            "Do you have any suggestions for how this could be improved? "
            "And is there anything about our service you'd like to praise?"
        ),
        "sw": (
            "Je, una mapendekezo ya jinsi hii inavyoweza kuboreshwa? "
            "Na je, kuna kitu chochote kuhusu huduma yetu ambacho ungependa kupongeza?"
        ),
    },
    "suggestion": {
        "en": (
            "Is there anything about our service or staff that you'd like to praise? "
            "And is there anything that's not working well that we should know about?"
        ),
        "sw": (
            "Je, kuna kitu chochote kuhusu huduma yetu au wafanyakazi ambacho "
            "ungependa kupongeza? "
            "Na je, kuna kitu ambacho hakifanyi kazi vizuri ambacho tunapaswa kujua?"
        ),
    },
    "applause": {
        "en": (
            "Thank you for the kind words! "
            "Do you have any suggestions for how we could make the service even better? "
            "Or is there anything that isn't working as well as it should?"
        ),
        "sw": (
            "Asante kwa maneno mazuri! "
            "Je, una mapendekezo ya jinsi ya kuboresha huduma zaidi? "
            "Au je, kuna kitu ambacho hakifanyi kazi vizuri kama inavyopaswa?"
        ),
    },
    "inquiry": {
        "en": (
            "Great — I hope that answered your question! "
            "Do you have any praise for our team? "
            "Or any suggestions or concerns we should know about?"
        ),
        "sw": (
            "Vizuri — natumaini hiyo ilijibu swali lako! "
            "Je, una pongezi kwa timu yetu? "
            "Au una mapendekezo au malalamiko yoyote ambayo tunapaswa kujua?"
        ),
    },
}


def build_closing_prompts(primary_type: str, language: str = "en") -> str:
    """
    Return cross-type follow-up questions to append after the primary feedback
    type is collected, at session close.
    """
    key  = (primary_type or "grievance").lower()
    lang = language if language in ("en", "sw") else "en"
    entry = _CLOSING_PROMPTS.get(key, _CLOSING_PROMPTS["grievance"])
    return entry.get(lang, entry["en"])


# ─────────────────────────────────────────────────────────────────────────────
# AI-10: Urgency classification
# ─────────────────────────────────────────────────────────────────────────────

# Phrase-level keywords checked before word tokenisation
_URGENCY_PHRASES = frozenset({
    "no power", "no water", "no electricity",
    "hakuna umeme", "hakuna maji",
    "cannot breathe", "chest pain",
})

# Single-word urgency keywords (English + Swahili)
_URGENCY_WORDS = frozenset({
    "urgent", "emergency", "critical", "immediately", "dying", "danger",
    "fire", "flood", "broken", "stuck", "locked", "cannot",
    # Swahili
    "haraka", "dharura", "hatari", "moto", "mafuriko",
    "imevunjika", "imefungwa", "sijui",
})


def classify_urgency(text: str) -> bool:
    """
    Return True if the text contains urgency keywords (English or Swahili).
    Used as a keyword fallback if the LLM did not flag is_urgent.
    """
    if not text:
        return False
    lower = text.lower()
    for phrase in _URGENCY_PHRASES:
        if phrase in lower:
            return True
    words = set(re.findall(r'\b\w+\b', lower))
    return bool(words & _URGENCY_WORDS)


# ─────────────────────────────────────────────────────────────────────────────
# AI-11: Tracking number delivery message
# ─────────────────────────────────────────────────────────────────────────────

def format_ref_message(ref_list: List[str], language: str = "en") -> str:
    """
    Format the reference number delivery message for session close.
    Always called when feedback is submitted.
    """
    refs = ", ".join(r for r in ref_list if r)
    if not refs:
        return ""
    if language == "sw":
        return (
            f"Nambari yako ya kufuatilia: {refs}. "
            "Tafadhali hifadhi nambari hii kwa ufuatiliaji."
        )
    return (
        f"Your reference number is {refs}. "
        "Please keep this for follow-up."
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI-12: Follow-up scheduling via Kafka
# ─────────────────────────────────────────────────────────────────────────────

async def schedule_followup(
    phone_number: str,
    feedback_ref: str,
    is_urgent: bool,
    org_id: Optional[str] = None,
    org_name: str = "",
) -> None:
    """
    Publish a follow-up notification request to Kafka.
    Urgent  → 30-minute delay, grm.followup.urgent template.
    Normal  → 24-hour delay,   grm.followup.normal template.
    Fire-and-forget — never raises.
    """
    if not phone_number or not feedback_ref:
        return
    try:
        from events.producer import get_producer
        from events.topics import KafkaTopics

        template      = "grm.followup.urgent" if is_urgent else "grm.followup.normal"
        delay_minutes = 30 if is_urgent else 1440  # 30 min or 24 h

        producer = await get_producer()
        await producer.publish(
            KafkaTopics.NOTIFICATIONS,
            "ai.followup.scheduled",
            {
                "notification_type":      template,
                "recipient":              {"phone": phone_number},
                "channels":               ["sms"],
                "variables": {
                    "feedback_ref": feedback_ref,
                    "org_name":     org_name or "our organisation",
                },
                "schedule_delay_minutes": delay_minutes,
                "org_id":                 org_id,
            },
            key=phone_number,
        )
        log.info("realtime.followup_scheduled",
                 ref=feedback_ref, urgent=is_urgent, delay_min=delay_minutes)
    except Exception as exc:
        log.warning("realtime.followup_schedule_error",
                    error=str(exc), ref=feedback_ref)


# ─────────────────────────────────────────────────────────────────────────────
# AI-13: Language detection + translation
# ─────────────────────────────────────────────────────────────────────────────

async def detect_and_translate(
    text: str,
    target_lang: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Detect language and optionally translate via translation_service.
    Returns {detected_lang, translated_text} or None on failure.
    """
    if not text or not text.strip():
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{settings.TRANSLATION_SERVICE_URL}/translate",
                json={
                    "text":        text,
                    "target_lang": target_lang,
                    "detect":      True,
                },
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code == 200:
            data = r.json()
            return {
                "detected_lang":   (
                    data.get("detected_lang")
                    or data.get("source_lang")
                    or "en"
                ),
                "translated_text": (
                    data.get("translated_text")
                    or data.get("translation")
                    or text
                ),
            }
        log.debug("realtime.translate_failed",
                  status=r.status_code, target=target_lang)
        return None
    except Exception as exc:
        log.warning("realtime.translate_error", error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-14: Transaction lookup
# ─────────────────────────────────────────────────────────────────────────────

async def lookup_transaction(
    reference: Optional[str] = None,
    phone:     Optional[str] = None,
    amount:    Optional[float] = None,
    org_id:    Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Look up a payment transaction by reference, phone, or amount.
    Returns transaction dict or None on failure/not-found.
    """
    params: Dict[str, Any] = {}
    if reference:
        params["reference"] = reference
    if phone:
        params["phone"] = phone
    if amount is not None:
        params["amount"] = amount
    if org_id:
        params["org_id"] = org_id
    if not params:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.PAYMENT_SERVICE_URL}/api/v1/internal/payments/lookup",
                params=params,
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as exc:
        log.warning("realtime.lookup_transaction_error", error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-15: Product verification
# ─────────────────────────────────────────────────────────────────────────────

async def verify_product(rsin_or_code: str) -> Optional[Dict[str, Any]]:
    """
    Check product authenticity via the verification service.
    Returns {status, product_name, org_name, is_authentic} or None on failure.
    """
    if not rsin_or_code:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.VERIFICATION_SERVICE_URL}"
                f"/api/v1/internal/verify/{rsin_or_code}",
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as exc:
        log.warning("realtime.verify_product_error", error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-16: Systemic hotspot detection
# ─────────────────────────────────────────────────────────────────────────────

async def check_systemic_pattern(
    org_id: str,
    category: str,
    description: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Query analytics hotspots endpoint.  If the user's complaint category /
    description overlaps an active hotspot, flag it as systemic.
    Returns {is_systemic, hotspot_description, affected_count} or None on error.
    """
    if not org_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.ANALYTICS_SERVICE_URL}"
                f"/api/v1/internal/analytics/{org_id}/hotspots",
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code != 200:
            return None
        body = r.json()
        hotspots = (
            body.get("hotspots")
            or (body if isinstance(body, list) else [])
        )
    except Exception as exc:
        log.warning("realtime.systemic_check_error", error=str(exc))
        return None

    if not hotspots:
        return {"is_systemic": False}

    cat_lower  = (category or "").lower()
    desc_lower = (description or "").lower()

    for hs in hotspots:
        hs_cat   = (hs.get("category") or "").lower()
        hs_title = (hs.get("title") or hs.get("label") or "").lower()

        # Category string overlap
        if hs_cat and cat_lower and (hs_cat in cat_lower or cat_lower in hs_cat):
            return {
                "is_systemic":         True,
                "hotspot_description": hs.get("title") or hs.get("description") or hs_cat,
                "affected_count":      hs.get("count") or hs.get("affected_count") or 0,
            }
        # Keyword overlap from description (need at least 2 words)
        if desc_lower and hs_title:
            overlap = set(desc_lower.split()) & set(hs_title.split())
            if len(overlap) >= 2:
                return {
                    "is_systemic":         True,
                    "hotspot_description": hs.get("title") or hs_title,
                    "affected_count":      hs.get("count") or 0,
                }

    return {"is_systemic": False}


# ─────────────────────────────────────────────────────────────────────────────
# AI-17: CMS knowledge pull
# ─────────────────────────────────────────────────────────────────────────────

async def get_org_content(org_id: str, topic: str) -> Optional[str]:
    """
    Fetch published CMS posts for the org and return the most relevant one
    for the given topic (keyword relevance scoring).
    Returns a short excerpt string, or None if nothing relevant found.
    """
    if not org_id or not topic:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.CMS_SERVICE_URL}/api/v1/internal/cms/{org_id}/posts",
                params={"status": "published", "limit": 20},
                headers=_INTERNAL_HEADERS,
            )
        if r.status_code != 200:
            return None
        body  = r.json()
        posts = (
            body.get("posts")
            or body.get("items")
            or (body if isinstance(body, list) else [])
        )
    except Exception as exc:
        log.warning("realtime.cms_content_error", error=str(exc))
        return None

    if not posts:
        return None

    topic_words = set(topic.lower().split())
    best_post   = None
    best_score  = 0

    for post in posts:
        title    = (post.get("title") or "").lower()
        excerpt  = (post.get("excerpt") or post.get("summary") or "").lower()
        body_txt = (post.get("body") or post.get("content") or "").lower()
        combined_words = set(f"{title} {excerpt} {body_txt}".split())
        score = len(topic_words & combined_words)
        if score > best_score:
            best_score = score
            best_post  = post

    if not best_post or best_score == 0:
        return None

    title   = best_post.get("title") or ""
    excerpt = best_post.get("excerpt") or best_post.get("summary") or ""
    body_fb = (best_post.get("body") or best_post.get("content") or "")[:500]
    return f"[CMS: {title}] {excerpt or body_fb}"


# ─────────────────────────────────────────────────────────────────────────────
# AI-21: Praised staff notification + performance flag
# ─────────────────────────────────────────────────────────────────────────────

async def notify_praised_staff(
    staff_id: str,
    staff_name: str,
    praise_note: str,
    feedback_ref: str,
    org_name: str,
) -> bool:
    """
    1. Send grm.staff.praised notification to the praised staff member.
    2. POST to staff service to record the praise on the performance record.
    Returns True when both succeed, False otherwise (partial failure also False).
    """
    if not staff_id or not feedback_ref:
        return False

    notification_ok = False
    performance_ok  = False

    # Step 1: Notify staff member
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/internal/notify",
                json={
                    "notification_type": "grm.staff.praised",
                    "recipient": {"staff_id": staff_id, "name": staff_name},
                    "channels": ["push", "sms"],
                    "variables": {
                        "staff_name":   staff_name,
                        "praise_note":  praise_note,
                        "feedback_ref": feedback_ref,
                        "org_name":     org_name,
                    },
                },
                headers=_INTERNAL_HEADERS,
            )
        notification_ok = r.status_code in (200, 201, 202)
        if not notification_ok:
            log.warning("realtime.praise_notify_failed",
                        status=r.status_code, staff_id=staff_id)
    except Exception as exc:
        log.warning("realtime.praise_notify_error", error=str(exc))

    # Step 2: Record performance flag on staff service
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{settings.STAFF_SERVICE_URL}/api/v1/staff/internal"
                f"/staff/{staff_id}/performance/flag",
                json={
                    "flag_type":    "praise",
                    "note":         praise_note,
                    "feedback_ref": feedback_ref,
                    "org_name":     org_name,
                },
                headers=_INTERNAL_HEADERS,
            )
        performance_ok = r.status_code in (200, 201, 202)
        if not performance_ok:
            log.warning("realtime.praise_flag_failed",
                        status=r.status_code, staff_id=staff_id)
    except Exception as exc:
        log.warning("realtime.praise_flag_error", error=str(exc))

    return notification_ok and performance_ok


# ─────────────────────────────────────────────────────────────────────────────
# AI-22: Voice / TTS text synthesis
# ─────────────────────────────────────────────────────────────────────────────

_NUMBER_WORDS_EN: Dict[int, str] = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
    10: "ten", 11: "eleven", 12: "twelve",
}

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FFFF"
    r"\U00002600-\U000027BF"
    r"\U0001F000-\U0001F02F"
    r"\U0001F0A0-\U0001F0FF"
    r"\U0001F100-\U0001F1FF"
    r"\U0001F200-\U0001F2FF"
    r"\U0001F900-\U0001F9FF"
    r"☀-⛿"
    r"✀-➿]+",
    flags=re.UNICODE,
)


def synthesize_response(text: str, lang: str = "en") -> str:
    """
    Format a text response for IVR/TTS delivery:
      - Strip markdown (bold, italic, headers, code fences, bullet markers)
      - Remove emoji
      - Spell out small numbers 0-12 (English only)
      - Ensure each sentence ends with a period for natural TTS pausing
      - Return plain text with no markup
    """
    if not text:
        return ""

    # Remove markdown
    cleaned = re.sub(r'#{1,6}\s+', '', text)          # ATX headers
    cleaned = re.sub(r'[*_`]+', '', cleaned)           # bold/italic/code
    cleaned = re.sub(r'^\s*[-•>]\s+', '', cleaned,    # bullets/blockquotes
                     flags=re.MULTILINE)
    # Remove inline links: [label](url) → label
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    # Remove bare URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    # Remove emoji
    cleaned = _EMOJI_RE.sub('', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if lang == "en":
        for num, word in _NUMBER_WORDS_EN.items():
            cleaned = re.sub(rf'\b{num}\b', word, cleaned)

    # Split at sentence boundaries, ensure each ends with terminal punctuation
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    tts_parts: List[str] = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if sent[-1] not in '.!?':
            sent += '.'
        tts_parts.append(sent)

    return ' '.join(tts_parts)


# ─────────────────────────────────────────────────────────────────────────────
# SLA deadline computation (used by AI-19 full attribution)
# ─────────────────────────────────────────────────────────────────────────────

def compute_sla_deadline(is_urgent: bool) -> str:
    """
    Return an ISO 8601 datetime string for the SLA deadline.
    Urgent: now + 4 hours.
    Normal: now + 48 hours.
    """
    delta = timedelta(hours=4) if is_urgent else timedelta(hours=48)
    return (datetime.now(timezone.utc) + delta).isoformat()
