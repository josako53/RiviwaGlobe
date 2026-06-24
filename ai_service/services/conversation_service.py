"""
services/conversation_service.py — Core AI conversation orchestrator.

Flow:
  Consumer sends message
  → find/create conversation session
  → check Consumer registration (by phone)
  → build RAG project context
  → call Ollama LLM
  → extract fields from LLM response
  → identify project via RAG if not yet set
  → check confidence → maybe auto-submit to feedback_service
  → handle urgency → attach incharge contact
  → return reply + state
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import ConversationNotFoundError, FeedbackSubmissionError
from models.conversation import (
    AIConversation, ConversationChannel, ConversationStatus, ConversationStage,
)
from repositories.conversation_repo import (
    ConversationRepository, ProjectKBRepository, StakeholderCacheRepository,
)
from services.ollama_service import get_ollama
from services.rag_service import get_rag
from services.feedback_client import FeedbackClient, submit_multiple_feedback
from services.auth_client import AuthClient
from services.stt_service import STTService

log = structlog.get_logger(__name__)

# ── Greetings ─────────────────────────────────────────────────────────────────
_GREETING_EN_BASE = (
    "Hello! I'm Riviwa AI, your Riviwa assistant. "
    "I can help you to get your voice heard right now.\n"
    "Do you have a grievance, suggestion, or applause?"
)
_GREETING_SW_BASE = (
    "Habari! Mimi ni Riviwa AI, msaidizi wako wa Riviwa. "
    "Ninaweza kukusaidia sauti yako isikike sasa hivi.\n"
    "Je, una malalamiko, mapendekezo, au shukrani?"
)


def _build_greeting(language: str, projects: list) -> str:
    """
    Build the opening greeting. If active projects are known, append a
    numbered list of locations so the Consumer can identify their project.
    """
    base = _GREETING_EN_BASE if language == "en" else _GREETING_SW_BASE

    if not projects:
        return base

    # Deduplicate locations: prefer "Name (Region / LGA)"
    seen: set = set()
    lines: list[str] = []
    for p in projects:
        parts = [p.name]
        geo = ", ".join(filter(None, [p.region, p.primary_lga]))
        if geo:
            parts.append(f"({geo})")
        label = " ".join(parts)
        if label not in seen:
            seen.add(label)
            lines.append(label)

    if not lines:
        return base

    if language == "en":
        loc_header = "\n\nHere are the active project areas — which one is near you?"
    else:
        loc_header = "\n\nHizi ni maeneo ya miradi inayoendelea — uko karibu na ipi?"

    numbered = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    return base + loc_header + "\n" + numbered
def _build_post_greeting(language: str, post_title: str) -> str:
    """Opening message when conversation is scoped to a CMS post."""
    if language == "en":
        return (
            f"Hello! I'm Riviwa, your feedback assistant.\n\n"
            f"You're giving feedback about: **{post_title}**\n\n"
            f"I can capture:\n"
            f"• 👏 Applause — if you appreciate something\n"
            f"• 💡 Suggestion — if you have an idea or improvement\n"
            f"• 🙁 Complaint — if something went wrong or was disappointing\n"
            f"• ❓ Inquiry — if you have a question\n\n"
            f"What would you like to share?"
        )
    return (
        f"Habari! Mimi ni Riviwa, msaidizi wa maoni.\n\n"
        f"Unatoa maoni kuhusu: **{post_title}**\n\n"
        f"Ninaweza kukusaidia na:\n"
        f"• 👏 Pongezi — kama unapenda kitu\n"
        f"• 💡 Pendekezo — kama una wazo au uboreshaji\n"
        f"• 🙁 Malalamiko — kama kuna tatizo au kitu kilikukatisha tamaa\n"
        f"• ❓ Maswali — kama una swali\n\n"
        f"Unataka kushiriki nini?"
    )


_FOLLOWUP_STATUS_SW = "Hali ya malalamiko yako ({}): {} — {}"
_FOLLOWUP_STATUS_EN = "Your feedback ({}) status: {} — {}"

_STATUS_LABELS = {
    "sw": {
        "submitted": "Imepokelewa", "acknowledged": "Imetambuliwa",
        "in_review": "Inachunguzwa", "escalated": "Imepelekwa juu",
        "resolved": "Imeshughulikiwa", "closed": "Imefungwa",
        "dismissed": "Imekataliwa",
    },
    "en": {
        "submitted": "Received", "acknowledged": "Acknowledged",
        "in_review": "Under review", "escalated": "Escalated",
        "resolved": "Resolved", "closed": "Closed",
        "dismissed": "Dismissed",
    },
}


def _make_analytics_token() -> str:
    """
    Generate a short-lived internal JWT to call analytics_service endpoints.
    Uses the same SECRET_KEY + HS256 algorithm the auth service signs with.
    Returns "" on any error so analytics enrichment degrades gracefully.
    """
    try:
        import time, uuid as _uuid
        import jwt as _jwt
        now = int(time.time())
        payload = {
            "sub":            "ai_service_internal",
            "jti":            str(_uuid.uuid4()),
            "iat":            now,
            "exp":            now + 300,          # 5-minute token
            "platform_role":  "super_admin",      # analytics endpoints require staff auth
        }
        return _jwt.encode(payload, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM)
    except Exception:
        return ""


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db        = db
        self.conv_repo = ConversationRepository(db)
        self.kb_repo   = ProjectKBRepository(db)
        self.sh_repo   = StakeholderCacheRepository(db)
        self.ollama    = get_ollama()
        self.rag       = get_rag()
        self.fb_client = FeedbackClient()
        self.auth_client = AuthClient()
        self.stt       = STTService()
        self._analytics_token: str = _make_analytics_token()

    # ── Public: start / resume ────────────────────────────────────────────────

    async def start_conversation(
        self,
        channel: str,
        language: str = "sw",
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        subproject_id: Optional[uuid.UUID] = None,
        branch_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        service_location_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        phone_number: Optional[str] = None,
        whatsapp_id: Optional[str] = None,
        web_token: Optional[str] = None,
        post_id: Optional[uuid.UUID] = None,
        post_slug: Optional[str] = None,
        post_title: Optional[str] = None,
    ) -> Tuple[AIConversation, str]:
        """
        Create a new conversation session and return (session, greeting_reply).
        org_id scopes the conversation to a specific organisation — RAG and
        project detection will only consider projects belonging to that org.
        When post_id is provided the conversation is scoped to a CMS post
        and the greeting asks for feedback about that specific post.
        """
        data = {
            "channel":            ConversationChannel(channel.lower()),
            "language":           language,
            "phone_number":       phone_number,
            "whatsapp_id":        whatsapp_id,
            "web_token":          web_token,
            "user_id":            user_id,
            "org_id":             org_id,
            "project_id":         project_id,
            "subproject_id":      subproject_id,
            "branch_id":          branch_id,
            "department_id":      department_id,
            "service_id":         service_id,
            "product_id":         product_id,
            "service_location_id": service_location_id,
            "post_id":            post_id,
            "post_slug":          post_slug,
            "post_title":         post_title,
        }
        conv = await self.conv_repo.create(data)

        if post_id:
            # Post-scoped conversation: build a post-aware greeting
            greeting = _build_post_greeting(language, post_title or post_slug or "this post")
        else:
            # Scope project suggestions to this org only (or show all for anonymous)
            active_projects = await self.kb_repo.list_active(org_id=org_id)
            greeting = _build_greeting(language, active_projects)

        # If project_id was pre-selected, look up its name
        if project_id:
            kb = await self.kb_repo.get_by_project_id(project_id)
            if kb:
                conv.project_name = kb.name

        # Check registration status if phone is known
        if phone_number:
            await self._check_registration(conv, phone_number)
        elif user_id:
            conv.is_registered = True

        # Record greeting turn
        conv.add_turn("assistant", greeting)
        conv.stage = ConversationStage.GREETING
        await self.conv_repo.save(conv)
        return conv, greeting

    async def process_message(
        self,
        conversation_id: uuid.UUID,
        message:    str,
        media_urls: Optional[List[str]] = None,
        audio_url:  Optional[str]       = None,
    ) -> Tuple[AIConversation, str, bool, List[dict]]:
        """
        Process a Consumer message. Returns (conv, reply, submitted, submitted_feedback_list).
        """
        conv = await self.conv_repo.get_or_404(conversation_id)

        if conv.status in (ConversationStatus.SUBMITTED, ConversationStatus.ABANDONED,
                           ConversationStatus.TIMED_OUT, ConversationStatus.FAILED):
            # Conversation is done — start fresh hint
            done_msg = (
                "Mazungumzo haya yamekwisha. Anza mazungumzo mapya."
                if conv.language == "sw"
                else "This conversation has ended. Please start a new session."
            )
            return conv, done_msg, False, []

        # Attach media URLs to extracted data
        if media_urls:
            existing = conv.get_extracted()
            existing_urls = existing.get("media_urls", [])
            existing_urls.extend(media_urls)
            conv.merge_extracted({"media_urls": existing_urls})

        # Check for timeout
        if self._is_timed_out(conv):
            conv.status = ConversationStatus.TIMED_OUT
            timeout_msg = (
                "Muda wa mazungumzo umekwisha. Tafadhali anza upya."
                if conv.language == "sw"
                else "Session timed out. Please start a new conversation."
            )
            conv.add_turn("assistant", timeout_msg)
            await self.conv_repo.save(conv)
            return conv, timeout_msg, False, []

        # Add Consumer's turn (with optional audio URL for voice messages)
        conv.add_turn("user", message, audio_url=audio_url)

        # Check follow-up pattern (reference number like GRV-2025-0042)
        if self._is_followup_query(message):
            reply = await self._handle_followup(conv, message)
            conv.add_turn("assistant", reply)
            await self.conv_repo.save(conv)
            return conv, reply, False, []

        # Build org context (branches, depts, services, products, categories, hours, projects)
        org_context = await self._build_org_context(conv)

        # Search Obsidian knowledge base for relevant GRM context
        knowledge_context = ""
        try:
            from services.obsidian_rag_service import get_obsidian_rag
            kb_results = get_obsidian_rag().search(message)
            if kb_results:
                knowledge_context = get_obsidian_rag().format_context(kb_results)
        except Exception as exc:
            log.warning("conversation.knowledge_search_failed", error=str(exc))

        # Fetch live analytics snapshot for the identified project
        analytics_context = ""
        if conv.project_id and self._analytics_token:
            try:
                from services.analytics_client import get_project_analytics_context
                analytics_context = await get_project_analytics_context(
                    conv.project_id, self._analytics_token
                )
            except Exception as exc:
                log.warning("conversation.analytics_context_failed", error=str(exc))

        # Call LLM
        try:
            llm_resp = await self.ollama.chat(
                messages=self._format_turns_for_llm(conv.get_turns()),
                org_context=org_context,
                knowledge_context=knowledge_context,
                analytics_context=analytics_context,
            )
        except Exception as exc:
            log.error("conversation.llm_failed", conv_id=str(conversation_id), error=str(exc))
            err_msg = (
                "Samahani, mfumo wa AI haukukubali sasa. Tafadhali jaribu tena."
                if conv.language == "sw"
                else "Sorry, the AI is temporarily unavailable. Please try again."
            )
            conv.add_turn("assistant", err_msg)
            await self.conv_repo.save(conv)
            return conv, err_msg, False, []

        reply         = llm_resp.get("reply", "")
        extracted_new = llm_resp.get("extracted", {})
        action        = llm_resp.get("action", "continue")

        # Merge extracted fields
        if extracted_new:
            conv.merge_extracted(extracted_new)
            # Update language from LLM detection
            if extracted_new.get("language"):
                conv.language = extracted_new["language"]

        # Resolve entity mentions (org/branch/dept/service/staff) + location
        await self._resolve_entities(conv, extracted_new or {})

        # Auto-identify project via RAG if not yet set
        await self._identify_project(conv)

        # Handle registration if user is not yet registered and we have their name
        if not conv.is_registered and conv.get_extracted().get("submitter_name") and conv.phone_number:
            await self._try_register(conv)

        # Urgency check
        if extracted_new.get("is_urgent") and not conv.is_urgent:
            conv.is_urgent = True
            incharge = await self.sh_repo.get_incharge_for_project(conv.project_id) if conv.project_id else None
            if incharge:
                conv.incharge_name  = incharge.name
                conv.incharge_phone = incharge.phone
                urgency_note = self._urgency_message(conv.language, incharge.name, incharge.phone)
                reply = f"{reply}\n\n{urgency_note}"

        # If user explicitly confirms AFTER the AI has shown a summary (stage=CONFIRMING) → force submit.
        # Restricted to CONFIRMING stage only — "Ndiyo" during collection is a general affirmative,
        # not a submission consent. Only fire after the AI has explicitly asked "Is this correct?"
        _CONFIRM_WORDS = {"ndio", "ndiyo", "yes", "wasilisha", "submit", "tuma", "sawa", "okay", "ok", "confirm", "endelea"}
        if conv.stage == ConversationStage.CONFIRMING and action not in ("submit", "followup"):
            msg_words = set(message.lower().replace(",", " ").replace(".", " ").split())
            if msg_words & _CONFIRM_WORDS:
                _ext = conv.get_extracted()
                _has_min = (
                    _ext.get("feedback_type") not in (None, "", "unknown")
                    and bool(_ext.get("description", "").strip())
                )
                if _has_min:
                    action = "submit"

        # Update stage
        conv.stage = self._map_action_to_stage(action)

        # Auto-submit check
        submitted = False
        submitted_feedback: List[dict] = []
        confidence = float(conv.get_extracted().get("confidence", 0.0))

        # Submit ONLY when user has explicitly confirmed (action=submit).
        # action=confirm means the AI wants to SHOW a summary and ask the user — do NOT submit yet.
        if action == "submit":
            submitted, submitted_feedback = await self._submit_feedback(conv)
            if submitted:
                ref_list = ", ".join(f["unique_ref"] for f in submitted_feedback)
                thanks = (
                    f"Asante! Malalamiko yako yamesajiliwa. Nambari yako ya kufuatilia: {ref_list}. "
                    f"Unaweza kufuatilia hali yako kwa kutumia nambari hii."
                    if conv.language == "sw"
                    else
                    f"Thank you! Your feedback has been submitted. Reference number(s): {ref_list}. "
                    f"Use this number to follow up on your submission."
                )
                reply = thanks
                conv.status = ConversationStatus.SUBMITTED
                conv.stage  = ConversationStage.DONE
                conv.completed_at = datetime.utcnow()

        conv.add_turn("assistant", reply)
        await self.conv_repo.save(conv)
        return conv, reply, submitted, submitted_feedback

    # ── Inbound channel handlers (SMS / WhatsApp webhooks) ────────────────────

    async def handle_inbound_sms(self, form: dict) -> str:
        """Process inbound SMS from Africa's Talking or Twilio. Returns reply text."""
        # Africa's Talking format
        phone   = form.get("from") or form.get("From") or form.get("phoneNumber", "")
        message = form.get("text") or form.get("Body", "")
        if not phone or not message:
            return ""
        conv = await self.conv_repo.find_active_by_phone(phone)
        if conv is None:
            conv, reply = await self.start_conversation(
                channel="sms", language="sw", phone_number=phone
            )
            return reply
        _, reply, _, _ = await self.process_message(conv.id, message)
        return reply

    async def handle_inbound_whatsapp(self, payload: dict) -> str:
        """Process inbound WhatsApp message. Returns reply text."""
        try:
            entry    = payload.get("entry", [{}])[0]
            changes  = entry.get("changes", [{}])[0]
            value    = changes.get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return ""
            msg      = messages[0]
            msg_type = msg.get("type", "text")
            from_id  = msg.get("from", "")
            if not from_id:
                return ""

            # Detect language hint from existing session
            language = "sw"
            existing = await self.conv_repo.find_active_by_whatsapp(from_id)
            if existing:
                language = existing.language or "sw"

            # Extract text
            if msg_type == "audio":
                media_id  = msg.get("audio", {}).get("id", "")
                transcript = await self.stt.process_whatsapp_voice(media_id, language) if media_id else None
                message_text = transcript or (
                    "Sauti imepokewa lakini haikuweza kubadilishwa kuwa maandishi. Tafadhali andika ujumbe."
                    if language == "sw"
                    else "Voice note received but could not be transcribed. Please type your message."
                )
            elif msg_type == "text":
                message_text = msg.get("text", {}).get("body", "")
            elif msg_type in ("image", "document"):
                # Collect media URL if available
                media = msg.get(msg_type, {})
                caption = media.get("caption", "")
                message_text = caption or (
                    "Picha/hati imepokelewa." if language == "sw" else "Media received."
                )
            else:
                return ""

            if not existing:
                existing, reply = await self.start_conversation(
                    channel="whatsapp", language=language, whatsapp_id=from_id
                )
                return reply

            _, reply, _, _ = await self.process_message(existing.id, message_text)
            return reply

        except Exception as exc:
            log.error("conversation.whatsapp_handler_error", error=str(exc), exc_info=exc)
            return ""

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _check_registration(self, conv: AIConversation, phone: str) -> None:
        user = await self.auth_client.find_user_by_phone(phone)
        if user:
            conv.is_registered = True
            conv.user_id       = uuid.UUID(user["id"])
            conv.submitter_name = user.get("full_name") or user.get("name")
            conv.merge_extracted({
                "submitter_name": conv.submitter_name,
                "user_id": str(conv.user_id),
            })

    async def _try_register(self, conv: AIConversation) -> None:
        name = conv.get_extracted().get("submitter_name", "")
        if not name or not conv.phone_number:
            return
        user = await self.auth_client.register_consumer(name=name, phone=conv.phone_number)
        if user:
            conv.is_registered = True
            conv.user_id       = uuid.UUID(user["id"])
            conv.merge_extracted({"user_id": str(conv.user_id)})
            log.info("conversation.consumer_registered", conv_id=str(conv.id), phone=conv.phone_number)

    async def _resolve_entities(self, conv: AIConversation, extracted_new: dict) -> None:
        """
        Resolve raw entity text mentions to UUIDs and location to coordinates.
        Runs after each LLM turn. Merges results back into conversation extracted data.
        Only runs when the LLM returned at least one mentionable field.
        """
        mention_fields = {
            "org_mentioned", "branch_mentioned", "department_mentioned",
            "service_mentioned", "staff_mentioned", "location_text",
            "gps_lat", "gps_lng", "categories_mentioned",
        }
        if not any(extracted_new.get(f) for f in mention_fields):
            return

        existing   = conv.get_extracted()
        org_id     = existing.get("org_id") or None
        enrichment: dict = {}

        # ── Entity resolution ─────────────────────────────────────────────────
        mentions = {k: extracted_new.get(k) for k in (
            "org_mentioned", "branch_mentioned", "department_mentioned",
            "service_mentioned", "staff_mentioned", "categories_mentioned",
        )}
        if any(mentions.values()):
            try:
                from services.entity_resolution_service import resolve_all
                resolved = resolve_all(mentions, org_id=org_id)
                for field in ("org_id", "branch_id", "department_id", "service_id", "product_id", "staff_id", "category_def_id"):
                    if resolved.get(field) and not existing.get(field):
                        enrichment[field] = resolved[field]
                if resolved.get("org_name") and not existing.get("org_name"):
                    enrichment["org_name"] = resolved["org_name"]
                if resolved.get("branch_name") and not existing.get("branch_name"):
                    enrichment["branch_name"] = resolved["branch_name"]
                if resolved.get("additional_category_ids") and not existing.get("additional_category_ids"):
                    enrichment["additional_category_ids"] = resolved["additional_category_ids"]
                log.debug("conversation.entities_resolved", conv_id=str(conv.id),
                          resolved={k: v for k, v in resolved.items() if v and k != "confidence"})
            except Exception as exc:
                log.warning("conversation.entity_resolution_error", conv_id=str(conv.id), error=str(exc))

        # ── Location resolution ───────────────────────────────────────────────
        gps_lat      = extracted_new.get("gps_lat")
        gps_lng      = extracted_new.get("gps_lng")
        location_text = extracted_new.get("location_text")

        if gps_lat or gps_lng or location_text:
            try:
                from services.location_service import resolve_location
                resolved_loc = await resolve_location(
                    gps_lat=float(gps_lat) if gps_lat else None,
                    gps_lng=float(gps_lng) if gps_lng else None,
                    location_text=location_text,
                    org_id=enrichment.get("org_id") or org_id,
                )
                if resolved_loc.get("city") and not existing.get("issue_location_description"):
                    enrichment["issue_location_description"] = resolved_loc["display_name"] or resolved_loc["city"]
                if resolved_loc.get("region") and not existing.get("region"):
                    enrichment["region"] = resolved_loc["region"]
                if resolved_loc.get("country_code") and not existing.get("country"):
                    enrichment["country"] = resolved_loc["country_code"]
                if resolved_loc.get("address_components"):
                    ac = resolved_loc["address_components"]
                    # Pull Tanzania-specific fields into standard slots if present
                    if ac.get("ward") and not existing.get("ward"):
                        enrichment["ward"] = ac["ward"]
                    if ac.get("lga") and not existing.get("lga"):
                        enrichment["lga"] = ac["lga"]
                    enrichment["address_components"] = ac
                if resolved_loc.get("latitude"):
                    enrichment["gps_lat"] = resolved_loc["latitude"]
                if resolved_loc.get("longitude"):
                    enrichment["gps_lng"] = resolved_loc["longitude"]
                # Nearest branch from GPS (only set if not already set)
                if resolved_loc.get("branch_id") and not existing.get("branch_id") and not enrichment.get("branch_id"):
                    enrichment["branch_id"] = resolved_loc["branch_id"]
                log.debug("conversation.location_resolved", conv_id=str(conv.id),
                          display=resolved_loc.get("display_name", "")[:80])
            except Exception as exc:
                log.warning("conversation.location_resolution_error", conv_id=str(conv.id), error=str(exc))

        if enrichment:
            conv.merge_extracted(enrichment)

    async def _identify_project(self, conv: AIConversation) -> None:
        """Use RAG to identify the project from extracted location/description."""
        if conv.project_id:
            return  # already set
        extracted = conv.get_extracted()
        query_parts = []
        if extracted.get("issue_location_description"):
            query_parts.append(extracted["issue_location_description"])
        if extracted.get("lga"):
            query_parts.append(extracted["lga"])
        if extracted.get("ward"):
            query_parts.append(extracted["ward"])
        if extracted.get("region"):
            query_parts.append(extracted["region"])
        if not query_parts:
            return
        query = " ".join(query_parts)

        # Try Qdrant semantic search first
        results = self.rag.search_projects(query, top_k=1, score_threshold=0.40)
        if results:
            project_id_str, score, payload = results[0]
            conv.project_id   = uuid.UUID(project_id_str)
            conv.project_name = payload.get("name")
            conv.merge_extracted({"project_id": project_id_str, "project_name": conv.project_name})
            log.info("conversation.project_identified_rag", conv_id=str(conv.id),
                     project=conv.project_name, score=score)
            return

        # Fallback: keyword search in DB
        matches = await self.kb_repo.keyword_search(query, limit=1)
        if matches:
            p = matches[0]
            conv.project_id   = p.project_id
            conv.project_name = p.name
            conv.merge_extracted({
                "project_id": str(p.project_id),
                "project_name": p.name,
            })
            log.info("conversation.project_identified_kw", conv_id=str(conv.id), project=p.name)

    async def _build_org_context(self, conv: AIConversation) -> str:
        """
        Build the full organisation context injected into the LLM system prompt.

        Priority order (most specific → most general):
          1. Org structure  — always first when org_id is known (branches, departments,
                              services, products, categories, industries, hours)
          2. Custom fields  — org-specific extra fields to collect during conversation
          3. Projects       — secondary, appended only if this org has active projects
          4. Anonymous      — no org_id: show all active projects across platform so the
                              AI can at least suggest a project to the consumer
        """
        parts: List[str] = []
        org_id = conv.org_id  # authoritative — never derive from projects

        if org_id:
            # 1. Org structure: branches, depts, services/products with prices, categories, hours
            org_struct = await self._fetch_org_structure(org_id)
            if org_struct:
                parts.append(org_struct)

            # 2. Custom field definitions
            custom_fields = await self._fetch_org_custom_fields(org_id)
            if custom_fields:
                parts.append(custom_fields)
        else:
            # Anonymous conversation — no org bound yet.
            # Show all active projects so the AI can help the consumer identify theirs.
            projects = await self.kb_repo.list_active()
            if projects:
                project_data = [
                    {
                        "project_id":           str(p.project_id),
                        "name":                 p.name,
                        "region":               p.region or "",
                        "primary_lga":          p.primary_lga or "",
                        "wards":                p.get_wards(),
                        "active_stage_name":    p.active_stage_name or "",
                        "status":               p.status,
                        "sector":               p.sector or "",
                        "category":             p.category or "",
                        "description":          p.description or "",
                        "objectives":           p.objectives or "",
                        "location_description": p.location_description or "",
                        "org_display_name":     p.org_display_name or "",
                        "code":                 p.code or "",
                    }
                    for p in projects[:10]
                ]
                parts.append(self.rag.build_project_context(project_data))

        return "\n\n".join(parts) if parts else "No organisation context available yet."

    async def _fetch_org_structure(self, org_id) -> str:
        """
        Fetch branches, departments, services, products from auth_service
        and format them as a compact context block for the LLM.
        Returns empty string on any failure — org structure is best-effort.
        """
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/internal/orgs/{org_id}/ai-context",
                    headers={
                        "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                        "X-Service-Name": "ai_service",
                    },
                )
            if r.status_code != 200:
                return ""
            raw = r.json()
        except Exception:
            return ""

        lines = ["ORG STRUCTURE — use these exact UUIDs when Consumer mentions any branch, department, service, or product:"]

        # Org identity
        org_name = raw.get("display_name") or raw.get("legal_name") or ""
        org_type = raw.get("org_type") or ""
        if org_name or org_type:
            lines.append(f"ORG: {org_name}" + (f" ({org_type})" if org_type else ""))

        # Industries
        industries = raw.get("industries") or []
        if industries:
            primary = [i["name"] for i in industries if i.get("is_primary")]
            others  = [i["name"] for i in industries if not i.get("is_primary")]
            ind_str = ", ".join(primary)
            if others:
                ind_str += "; also: " + ", ".join(others[:5])
            lines.append(f"INDUSTRIES: {ind_str}")

        # Operating hours
        hours = raw.get("operating_hours") or []
        open_days = [
            f"{h['day'].capitalize()} {h['open']}-{h['close']}"
            for h in hours
            if h.get("is_open") and h.get("open") and h.get("close")
        ]
        if open_days:
            lines.append("OPEN HOURS: " + ", ".join(open_days))

        # Branches
        branches = raw.get("branches", [])
        if branches:
            parts = []
            for b in branches[:15]:
                s = f"{b['name']} (id={b['id']}"
                geo = ", ".join(filter(None, [b.get("city"), b.get("region")]))
                if geo:
                    s += f", {geo}"
                if b.get("phone"):
                    s += f", tel={b['phone']}"
                s += ")"
                parts.append(s)
            lines.append("BRANCHES: " + "; ".join(parts))

        # Departments
        depts = raw.get("departments", [])
        if depts:
            lines.append("DEPARTMENTS: " + "; ".join(
                f"{d['name']} (id={d['id']})" for d in depts[:20]
            ))

        # Services and Products (with price if available)
        all_svcs = raw.get("services", [])
        services = [s for s in all_svcs if (s.get("service_type") or "").upper() != "PRODUCT"]
        products = [s for s in all_svcs if (s.get("service_type") or "").upper() == "PRODUCT"]

        def _svc_label(s: dict) -> str:
            label = f"{s['title']} (id={s['id']}"
            price = s.get("base_price")
            currency = s.get("currency_code") or "TZS"
            if price is not None:
                label += f", price={currency} {price:,.0f}"
            mode = s.get("delivery_mode")
            if mode:
                label += f", mode={mode}"
            summary = (s.get("summary") or "")[:80]
            if summary:
                label += f", desc={summary}"
            label += ")"
            return label

        if services:
            lines.append("SERVICES: " + "; ".join(_svc_label(s) for s in services[:20]))
        if products:
            lines.append("PRODUCTS: " + "; ".join(_svc_label(p) for p in products[:20]))

        # Feedback categories (fetched from feedback_service)
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=4) as cl:
                cr = await cl.get(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/internal/categories/ai-context",
                    params={"org_id": str(org_id)},
                    headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
                )
            if cr.status_code == 200:
                cats = cr.json().get("categories") or []
                if cats:
                    cat_parts = []
                    for c in cats[:30]:
                        slug = c.get("slug") or c.get("name", "").lower().replace(" ", "_")
                        fbt  = ", ".join(c.get("feedback_types") or [])
                        s = f"{c['name']} (id={c['id']}, slug={slug}"
                        if fbt:
                            s += f", types={fbt}"
                        desc = (c.get("description") or "")[:60]
                        if desc:
                            s += f", desc={desc}"
                        s += ")"
                        cat_parts.append(s)
                    lines.append("FEEDBACK CATEGORIES (resolve categories_mentioned to one of these IDs): " + "; ".join(cat_parts))
        except Exception:
            pass

        # Projects belonging to this org
        try:
            org_projects = await self.kb_repo.list_active(org_id=org_id)
            if org_projects:
                proj_parts = []
                for p in org_projects[:15]:
                    s = f"{p.name} (id={p.project_id}"
                    if p.active_stage_name:
                        s += f", stage={p.active_stage_name}"
                    if p.region:
                        s += f", region={p.region}"
                    if p.primary_lga:
                        s += f", lga={p.primary_lga}"
                    if p.sector:
                        s += f", sector={p.sector}"
                    if p.code:
                        s += f", code={p.code}"
                    s += ")"
                    proj_parts.append(s)
                lines.append("PROJECTS: " + "; ".join(proj_parts))
        except Exception:
            pass

        return "\n".join(lines) if len(lines) > 1 else ""

    async def _fetch_org_custom_fields(self, org_id) -> str:
        """
        Fetch org-specific custom field definitions from auth_service and format them
        as a context block instructing the LLM which extra fields to collect.
        Returns empty string on any failure — custom fields are best-effort.
        """
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/orgs/{org_id}/custom-fields/ai-context",
                    headers={
                        "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                        "X-Service-Name": "ai_service",
                    },
                )
            if r.status_code != 200:
                return ""
            raw = r.json()
        except Exception:
            return ""

        # raw is expected: {"feedback": [...], "stakeholder": [...]}
        feedback_fields = raw.get("feedback", [])
        if not feedback_fields:
            return ""

        lines = [
            "ORGANISATION CUSTOM FIELDS (collect these during conversation in addition to standard fields):",
        ]
        lines.append("Entity: FEEDBACK")
        lines.append("Fields to collect:")
        for f in feedback_fields:
            key       = f.get("field_key", "")
            label     = f.get("label") or key
            label_sw  = f.get("label_sw") or ""
            required  = f.get("is_required", False)
            req_label = "Required" if required else "Optional"
            combined  = f"{label} / {label_sw}" if label_sw else label
            lines.append(f"  - {key} ({combined}): {req_label}")

        lines.append(
            'When submitting, include these as custom_fields: {'
            + ", ".join(
                f'"{f.get("field_key", "")}" : "<value>"'
                for f in feedback_fields
            )
            + "}"
        )

        # Also mention stakeholder fields if present
        stakeholder_fields = raw.get("stakeholder", [])
        if stakeholder_fields:
            lines.append("Entity: STAKEHOLDER")
            lines.append("Fields to collect:")
            for f in stakeholder_fields:
                key       = f.get("field_key", "")
                label     = f.get("label") or key
                label_sw  = f.get("label_sw") or ""
                required  = f.get("is_required", False)
                req_label = "Required" if required else "Optional"
                combined  = f"{label} / {label_sw}" if label_sw else label
                lines.append(f"  - {key} ({combined}): {req_label}")

        return "\n".join(lines)

    async def _submit_feedback(
        self, conv: AIConversation
    ) -> Tuple[bool, List[dict]]:
        """Submit all feedback items extracted from the conversation."""
        extracted = conv.get_extracted()

        # If the LLM's extracted description is brief, enrich it with the verbatim
        # user messages so no detail is lost (patient IDs, doctor names, dates, etc.)
        extracted_desc = (extracted.get("description") or "").strip()
        user_msgs = " | ".join(
            t["content"] for t in conv.get_turns()
            if t.get("role") == "user" and t.get("content", "").strip()
        )
        if user_msgs and len(extracted_desc) < len(user_msgs) * 0.5:
            enriched = f"{extracted_desc}\n\n[Original message(s): {user_msgs}]" if extracted_desc else user_msgs
            extracted = {**extracted, "description": enriched}

        def _sid(field) -> Optional[str]:
            return str(field) if field else None

        common_data = {
            **extracted,
            # Authoritative context — conv-stored values win over anything the LLM may
            # have guessed; extracted values fill gaps when not pre-bound at start time.
            "org_id":              _sid(conv.org_id) or extracted.get("org_id"),
            "project_id":          extracted.get("project_id") or _sid(conv.project_id),
            "subproject_id":       extracted.get("subproject_id") or _sid(conv.subproject_id),
            "branch_id":           extracted.get("branch_id") or _sid(conv.branch_id),
            "department_id":       extracted.get("department_id") or _sid(conv.department_id),
            "service_id":          extracted.get("service_id") or _sid(conv.service_id),
            "product_id":          extracted.get("product_id") or _sid(conv.product_id),
            "service_location_id": extracted.get("service_location_id") or _sid(conv.service_location_id),
            # Category context
            "category_def_id":          extracted.get("category_def_id"),
            "additional_category_ids":  extracted.get("additional_category_ids") or [],
            "suggested_category_names": extracted.get("suggested_category_names") or [],
            # Conversation meta
            "phone_number":        conv.phone_number or conv.whatsapp_id,
            "user_id":             _sid(conv.user_id),
            "channel":             conv.channel.value,
            # CMS post context
            "post_id":             _sid(conv.post_id),
            "post_slug":           conv.post_slug,
        }

        if extracted.get("multiple_issues") and extracted.get("feedback_items"):
            items = extracted["feedback_items"]
            results = await submit_multiple_feedback(self.fb_client, items, common_data)
        else:
            try:
                resp = await self.fb_client.submit_staff(common_data)
                results = [{
                    "feedback_id": str(resp.get("id", "")),
                    "unique_ref": resp.get("unique_ref", ""),
                    "feedback_type": extracted.get("feedback_type", "grievance"),
                }]
            except FeedbackSubmissionError as exc:
                log.error("conversation.submit_failed", conv_id=str(conv.id), error=str(exc))
                return False, []

        if results:
            existing = conv.get_submitted()
            existing.extend(results)
            conv.submitted_feedback = existing
            return True, results

        return False, []

    async def _handle_followup(self, conv: AIConversation, message: str) -> str:
        """Look up feedback status when Consumer provides a reference number."""
        ref = self._extract_ref_number(message)
        if not ref:
            return (
                "Samahani, sikuweza kupata nambari ya kufuatilia. Tafadhali andika nambari yako kama vile GRV-2025-0042."
                if conv.language == "sw"
                else "Sorry, I couldn't find a tracking number. Please provide it like GRV-2025-0042."
            )
        feedback = await self.fb_client.get_feedback_by_ref(ref)
        if not feedback:
            return (
                f"Nambari {ref} haikupatikana. Tafadhali angalia nambari na ujaribu tena."
                if conv.language == "sw"
                else f"Reference {ref} not found. Please check the number and try again."
            )
        status_key  = feedback.get("status", "submitted").lower()
        lang        = conv.language
        labels      = _STATUS_LABELS.get(lang, _STATUS_LABELS["en"])
        status_label = labels.get(status_key, status_key.replace("_", " ").title())
        description = feedback.get("description", "")[:100]
        conv.status = ConversationStatus.FOLLOWUP
        conv.stage  = ConversationStage.FOLLOWUP
        if lang == "sw":
            return (
                f"Hali ya {ref}: **{status_label}**\n"
                f"Maelezo: {description}\n"
                f"Je, una swali lingine au unataka kutoa malalamiko mapya?"
            )
        return (
            f"Status of {ref}: **{status_label}**\n"
            f"Description: {description}\n"
            f"Do you have another question or would you like to submit new feedback?"
        )

    @staticmethod
    def _extract_ref_number(text: str) -> Optional[str]:
        import re
        m = re.search(r'\b(GRV|SGG|APP)-\d{4}-\d{4}\b', text.upper())
        return m.group(0) if m else None

    @staticmethod
    def _is_followup_query(text: str) -> bool:
        import re
        return bool(re.search(r'\b(GRV|SGG|APP)-\d{4}-\d{4}\b', text.upper()))

    @staticmethod
    def _is_timed_out(conv: AIConversation) -> bool:
        from datetime import timedelta
        timeout = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)
        return datetime.now(timezone.utc) - conv.last_active_at.replace(tzinfo=timezone.utc) > timeout

    @staticmethod
    def _map_action_to_stage(action: str) -> ConversationStage:
        mapping = {
            "continue":      ConversationStage.COLLECTING,
            "confirm":       ConversationStage.CONFIRMING,
            "submit":        ConversationStage.CONFIRMING,
            "followup":      ConversationStage.FOLLOWUP,
            "register_user": ConversationStage.IDENTIFY,
            "done":          ConversationStage.DONE,
        }
        return mapping.get(action, ConversationStage.COLLECTING)

    @staticmethod
    def _format_turns_for_llm(turns: list) -> list:
        """Convert stored turns to Ollama message format (exclude system prompt)."""
        return [
            {"role": t["role"], "content": t["content"]}
            for t in turns
            if t.get("role") in ("user", "assistant")
        ]

    @staticmethod
    def _urgency_message(language: str, name: str, phone: str) -> str:
        if language == "sw":
            return (
                f"⚠️ Tatizo hili ni la dharura. Tafadhali wasiliana moja kwa moja na "
                f"Afisa Mradi ({name}) kwa nambari: {phone}."
            )
        return (
            f"⚠️ This issue appears urgent. Please contact the Project Officer "
            f"({name}) directly at: {phone}."
        )
