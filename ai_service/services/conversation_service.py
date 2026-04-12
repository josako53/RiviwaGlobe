"""
services/conversation_service.py — Core AI conversation orchestrator.

Flow:
  PAP sends message
  → find/create conversation session
  → check PAP registration (by phone)
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
    numbered list of locations so the PAP can identify their project.
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

    # ── Public: start / resume ────────────────────────────────────────────────

    async def start_conversation(
        self,
        channel: str,
        language: str = "sw",
        project_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        phone_number: Optional[str] = None,
        whatsapp_id: Optional[str] = None,
        web_token: Optional[str] = None,
    ) -> Tuple[AIConversation, str]:
        """
        Create a new conversation session and return (session, greeting_reply).
        """
        # Load active projects so we can suggest locations in the greeting
        active_projects = await self.kb_repo.list_active()
        greeting = _build_greeting(language, active_projects)
        data = {
            "channel": ConversationChannel(channel.lower()),
            "language": language,
            "phone_number": phone_number,
            "whatsapp_id": whatsapp_id,
            "web_token": web_token,
            "user_id": user_id,
            "project_id": project_id,
        }
        conv = await self.conv_repo.create(data)

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
        message: str,
        media_urls: Optional[List[str]] = None,
    ) -> Tuple[AIConversation, str, bool, List[dict]]:
        """
        Process a PAP message. Returns (conv, reply, submitted, submitted_feedback_list).
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

        # Add PAP's turn
        conv.add_turn("user", message)

        # Check follow-up pattern (reference number like GRV-2025-0042)
        if self._is_followup_query(message):
            reply = await self._handle_followup(conv, message)
            conv.add_turn("assistant", reply)
            await self.conv_repo.save(conv)
            return conv, reply, False, []

        # Build project context for RAG injection
        project_context = await self._build_project_context(conv)

        # Search Obsidian knowledge base for relevant GRM context
        knowledge_context = ""
        try:
            from services.obsidian_rag_service import get_obsidian_rag
            kb_results = get_obsidian_rag().search(message)
            if kb_results:
                knowledge_context = get_obsidian_rag().format_context(kb_results)
        except Exception as exc:
            log.warning("conversation.knowledge_search_failed", error=str(exc))

        # Call LLM
        try:
            llm_resp = await self.ollama.chat(
                messages=self._format_turns_for_llm(conv.get_turns()),
                project_context=project_context,
                knowledge_context=knowledge_context,
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

        # Update stage
        conv.stage = self._map_action_to_stage(action)

        # Auto-submit check
        submitted = False
        submitted_feedback: List[dict] = []
        confidence = float(conv.get_extracted().get("confidence", 0.0))

        if action in ("submit", "confirm") and confidence >= settings.AUTO_SUBMIT_CONFIDENCE:
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
                conv.completed_at = datetime.now(timezone.utc)

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
        user = await self.auth_client.register_pap(name=name, phone=conv.phone_number)
        if user:
            conv.is_registered = True
            conv.user_id       = uuid.UUID(user["id"])
            conv.merge_extracted({"user_id": str(conv.user_id)})
            log.info("conversation.pap_registered", conv_id=str(conv.id), phone=conv.phone_number)

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

    async def _build_project_context(self, conv: AIConversation) -> str:
        """Build project context string to inject into the system prompt."""
        projects = await self.kb_repo.list_active()
        if not projects:
            return "No active projects."
        data = [
            {
                "project_id": str(p.project_id),
                "name": p.name,
                "region": p.region or "",
                "primary_lga": p.primary_lga or "",
                "wards": p.get_wards(),
                "active_stage_name": p.active_stage_name or "",
                "status": p.status,
            }
            for p in projects[:10]  # cap at 10 to keep prompt size manageable
        ]
        return self.rag.build_project_context(data)

    async def _submit_feedback(
        self, conv: AIConversation
    ) -> Tuple[bool, List[dict]]:
        """Submit all feedback items extracted from the conversation."""
        extracted = conv.get_extracted()

        if not extracted.get("project_id") and not conv.project_id:
            log.warning("conversation.submit_no_project", conv_id=str(conv.id))
            return False, []

        common_data = {
            **extracted,
            "project_id": extracted.get("project_id") or (str(conv.project_id) if conv.project_id else None),
            "phone_number": conv.phone_number or conv.whatsapp_id,
            "user_id": str(conv.user_id) if conv.user_id else None,
            "channel": conv.channel.value,
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
        """Look up feedback status when PAP provides a reference number."""
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
