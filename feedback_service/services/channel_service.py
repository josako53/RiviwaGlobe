"""
services/channel_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for two-way channel sessions:
  · LLM conversation engine (Claude claude-sonnet-4-6)
  · Session state machine (ACTIVE → COMPLETED / TIMED_OUT / ABANDONED)
  · Auto-submission when confidence ≥ 0.80 or MAX_TURNS reached
  · auth_service channel registration (non-blocking)
  · Inbound webhook processing (SMS / WhatsApp)
  · Language detection (Swahili vs English)
"""
from __future__ import annotations

import json as _json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import structlog

def _to_uuid(v) -> uuid.UUID:
    """Accept both uuid.UUID objects (from Pydantic) and plain strings."""
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))


from core.config import settings
from core.exceptions import NotFoundError, ValidationError
from models.feedback import (
    CategoryStatus,
    ChannelSession,
    Feedback,
    FeedbackCategory,
    FeedbackChannel,
    FeedbackCategoryDef,
    FeedbackPriority,
    FeedbackStatus,
    FeedbackType,
    GRMLevel,
    SessionStatus,
    SubmissionMethod,
)
from repositories.channel_repository import ChannelRepository
from repositories.feedback_repository import FeedbackRepository
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

SESSION_TIMEOUT_MINUTES = 30
MAX_TURNS = 20

_SYSTEM_PROMPT_SW = """Wewe ni Riviwa AI — msaidizi wa akili wa Riviwa, jukwaa linalohakikisha huduma bora
na bidhaa za ubora wa juu kwa wakati halisi kupitia maoni, kwa shirika lolote duniani:
hospitali, benki, serikali, NGO, balozi, wachuuzi, programu za kilimo, shule, mikahawa,
majukwaa ya biashara ya mtandaoni, na mengine mengi.

Jukumu lako ni kusikiliza mtu na kuelewa anachotaka kushiriki, kisha umsaidie
kueleza wazi ili iweze kuwasilishwa kwa shirika husika.

Aina nne za maoni:
- MALALAMIKO (grievance): kutoridhika, lalamiko, au hisia ya kudhulumiwa au kuumizwa na tatizo.
  Riviwa AI inatatua au kupunguza tatizo kwa wakati halisi.
- PENDEKEZO (suggestion): ushauri au mapendekezo jinsi mambo yanavyopaswa kuboreshwa au
  kushughulikiwa. Riviwa AI inatekeleza kwa wakati halisi iwezekanavyo.
- PONGEZI (applause): sifa au shukrani za huduma, bidhaa, mfanyakazi, idara, au shirika.
  Riviwa AI inasambaza utambuzi huu kwa wafanyakazi na idara zote husika.
- MASWALI (inquiry): swali au ombi la taarifa — kutaka kuelewa jinsi kitu kinavyofanya kazi,
  hali ya ombi, masaa ya kufungua, au kutatua wasiwasi. Riviwa AI inajibu kwa wakati halisi.

KANUNI MUHIMU:
- GUNDUA aina ya maoni kutoka kwa maneno ya mtu — USIWAULIZE waainishe wenyewe. Tambua kutoka muktadha.
- Uliza swali MOJA kwa wakati mmoja, kwa upole.
- Kuwa na joto na mazungumzo — usikuwe rasmi mno.
- Unapopata taarifa za kutosha (confidence ≥ 0.80), toa muhtasari na uomba uthibitisho.
- Jibu kwa lugha ambayo mtumiaji anaandika.
- USITAJE "mradi wa miundombinu" — Riviwa inahudumia sekta na shirika lolote duniani.

Baada ya kila ujumbe wa mtumiaji, rudisha JSON hii TU (bila maelezo mengine):
{
  "reply": "<jibu lako kwa mtumiaji>",
  "extracted": {
    "feedback_type": "grievance|suggestion|applause|inquiry|null",
    "subject": "<muhtasari au null>",
    "description": "<maelezo kamili au null>",
    "category_slug": "<slug kutoka orodha au null>",
    "lga": "<eneo au null>",
    "ward": "<kata au null>",
    "incident_date": "<YYYY-MM-DD au null>",
    "submitter_name": "<jina au null>",
    "is_anonymous": true|false
  },
  "confidence": 0.0,
  "ready_to_submit": false,
  "language": "sw|en"
}"""

_SYSTEM_PROMPT_EN = """You are Riviwa AI — an intelligent assistant for Riviwa, the platform that ensures
excellent service and high-quality products in real time through feedback, for any organisation
worldwide: hospitals, banks, governments, NGOs, embassies, retailers, agriculture programs,
schools, restaurants, e-commerce platforms, and many more.

Your role is to listen to the person, understand what they want to share, and help them
articulate it clearly so it reaches the right people in the organisation.

The four types of feedback:
- GRIEVANCE: dissatisfaction, complaint, or feeling of being treated unfairly — a problem
  the person experienced with a service, product, or staff. Riviwa AI solves or reduces the problem.
- SUGGESTION: advice or recommendation on how things should be improved or handled differently.
  Riviwa AI implements it in real-time where possible.
- APPLAUSE: praise or compliment of a service, product, staff member, department, or organisation.
  Riviwa AI multiplies this recognition to all relevant staff and departments.
- INQUIRY: a question or request for information — wanting to know how something works,
  check availability or status, understand a process, or resolve doubt. Riviwa AI clarifies
  and answers in real-time from the organisation's knowledge.

CRITICAL RULES:
- DETECT the feedback type from what the person says — do NOT ask them to classify it themselves.
  Infer from context: complaints → grievance, "I think you should" → suggestion, praise → applause,
  "how do I / what is / when does" → inquiry.
- Ask ONE question at a time, politely.
- Be warm and conversational — never clinical or bureaucratic.
- When you have enough information (confidence ≥ 0.80), summarise and ask for confirmation.
- Reply in the same language the user writes in.
- Do NOT frame this as "a project" — Riviwa serves any sector and any organisation worldwide.

After each user message, return ONLY this JSON (no other text):
{
  "reply": "<your reply to the user>",
  "extracted": {
    "feedback_type": "grievance|suggestion|applause|inquiry|null",
    "subject": "<summary or null>",
    "description": "<full description or null>",
    "category_slug": "<slug from list or null>",
    "lga": "<location/area or null>",
    "ward": "<sub-location or null>",
    "incident_date": "<YYYY-MM-DD or null>",
    "submitter_name": "<name or null>",
    "is_anonymous": true|false
  },
  "confidence": 0.0,
  "ready_to_submit": false,
  "language": "sw|en"
}"""


class ChannelService:

    def __init__(self, db: AsyncSession) -> None:
        self.repo    = ChannelRepository(db)
        self.fb_repo = FeedbackRepository(db)
        self.db      = db

    # ── Session CRUD ──────────────────────────────────────────────────────────

    async def create_session(
        self, data: dict, created_by: uuid.UUID
    ) -> ChannelSession:
        channel = FeedbackChannel(data["channel"])
        if channel not in (FeedbackChannel.SMS, FeedbackChannel.WHATSAPP, FeedbackChannel.PHONE_CALL):
            raise ValidationError("channel must be sms, whatsapp, or phone_call for a two-way session.")

        session = ChannelSession(
            channel             = channel,
            project_id          = _to_uuid(data["project_id"]) if data.get("project_id") else None,
            phone_number        = data.get("phone_number"),
            whatsapp_id         = data.get("whatsapp_id"),
            gateway_session_id  = data.get("gateway_session_id"),
            gateway_provider    = data.get("gateway_provider", "other"),
            language            = data.get("language", "sw"),
            is_officer_assisted = bool(data.get("is_officer_assisted", False)),
            recorded_by_user_id = created_by if data.get("is_officer_assisted") else None,
        )
        session = await self.repo.create(session)

        opening = (
            "Habari! Mimi ni Riviwa AI. "
            "Niambie — una tatizo, pendekezo, pongezi, au swali? "
            "Niko hapa kukusaidia."
        ) if session.language == "sw" else (
            "Hello! I'm Riviwa AI. "
            "What would you like to share today — a complaint, suggestion, praise, or question? "
            "I'm here to help."
        )
        session.add_turn("assistant", opening)
        await self.repo.save(session)
        await self.db.commit()
        return session

    async def get_or_404(self, session_id: uuid.UUID) -> ChannelSession:
        s = await self.repo.get_by_id(session_id)
        if not s:
            raise NotFoundError(message="Channel session not found.")
        return s

    async def list(self, **filters) -> list[ChannelSession]:
        return await self.repo.list(**filters)

    async def abandon(self, session_id: uuid.UUID, data: dict) -> ChannelSession:
        s = await self.get_or_404(session_id)
        s.status      = SessionStatus.ABANDONED
        s.end_reason  = data.get("reason", "Manually abandoned by staff.")
        s.completed_at = datetime.now(timezone.utc)
        await self.repo.save(s)
        await self.db.commit()
        return s

    # ── Turn processing ───────────────────────────────────────────────────────

    async def process_message(
        self, session_id: uuid.UUID, message: str
    ) -> dict:
        s = await self.get_or_404(session_id)
        if s.status != SessionStatus.ACTIVE:
            raise ValidationError(f"Session is {s.status.value} — cannot add messages.")
        reply, submitted = await self._process_turn(s, message)
        return {
            "session_id":  str(s.id),
            "reply":       reply,
            "submitted":   submitted,
            "feedback_id": str(s.feedback_id) if s.feedback_id else None,
            "status":      s.status.value,
            "turn_count":  s.turn_count,
        }

    async def force_submit(self, session_id: uuid.UUID) -> dict:
        s = await self.get_or_404(session_id)
        if s.feedback_id:
            return {"message": "Already submitted.", "feedback_id": str(s.feedback_id)}
        if not s.project_id:
            raise ValidationError("project_id must be set before submitting.")
        submitted = await self._auto_submit(s)
        await self.db.commit()
        return {
            "submitted":   submitted,
            "feedback_id": str(s.feedback_id) if s.feedback_id else None,
            "status":      s.status.value,
        }

    # ── Inbound webhooks ──────────────────────────────────────────────────────

    async def handle_inbound_sms(self, body_dict: dict) -> str:
        phone      = body_dict.get("phoneNumber") or body_dict.get("From", "")
        message    = body_dict.get("text") or body_dict.get("Body", "")
        session_id = body_dict.get("sessionId") or body_dict.get("MessageSid", "")
        provider   = "africas_talking" if "phoneNumber" in body_dict else "twilio"
        if not phone or not message:
            return ""
        return await self._handle_inbound(FeedbackChannel.SMS, phone, message, session_id, provider)

    async def handle_inbound_whatsapp(self, payload: dict) -> None:
        try:
            msg     = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            wa_id   = msg["from"]
            message = msg.get("text", {}).get("body", "")
            msg_id  = msg.get("id", "")
        except (KeyError, IndexError):
            return
        if not message:
            return
        await self._handle_inbound(FeedbackChannel.WHATSAPP, wa_id, message, msg_id, "meta")

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _handle_inbound(
        self, channel: FeedbackChannel, identifier: str,
        message: str, gateway_session_id: str, provider: str,
    ) -> str:
        from sqlalchemy import select as sa_select
        id_field = (
            ChannelSession.whatsapp_id
            if channel == FeedbackChannel.WHATSAPP
            else ChannelSession.phone_number
        )
        result = await self.db.execute(
            sa_select(ChannelSession).where(
                id_field              == identifier,
                ChannelSession.channel == channel,
                ChannelSession.status  == SessionStatus.ACTIVE,
            ).order_by(ChannelSession.started_at.desc()).limit(1)
        )
        session = result.scalar_one_or_none()

        if session:
            timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            if session.last_activity_at < timeout_threshold:
                session.status      = SessionStatus.TIMED_OUT
                session.completed_at = datetime.now(timezone.utc)
                await self.repo.save(session)
                await self.db.commit()
                session = None

        if not session:
            lang    = self._detect_language(message)
            session = ChannelSession(
                channel            = channel,
                phone_number       = identifier if channel != FeedbackChannel.WHATSAPP else None,
                whatsapp_id        = identifier if channel == FeedbackChannel.WHATSAPP else None,
                gateway_session_id = gateway_session_id,
                gateway_provider   = provider,
                language           = lang,
            )
            session = await self.repo.create(session)
            user_id = await self._register_with_auth(identifier, channel.value, lang)
            if user_id:
                session.user_id = user_id
                await self.repo.save(session)
            opening = (
                "Habari! Mimi ni Riviwa AI. Niambie — una tatizo, pendekezo, pongezi, au swali? "
                "Niko hapa kukusaidia."
            ) if lang == "sw" else (
                "Hello! I'm Riviwa AI. What would you like to share — a complaint, suggestion, praise, or question? "
                "I'm here to help."
            )
            session.add_turn("assistant", opening)
            await self.repo.save(session)
            await self.db.commit()
            await self.db.refresh(session)

        reply, _ = await self._process_turn(session, message)
        return reply

    async def _process_turn(
        self, session: ChannelSession, user_message: str
    ) -> tuple[str, bool]:
        session.add_turn("user", user_message)
        active_cats = await self.repo.list_active_categories(session.project_id) if session.project_id else []
        result     = await self._call_llm(session, active_cats)
        reply      = result.get("reply", "...")
        extracted  = result.get("extracted", {})
        confidence = float(result.get("confidence", 0.0))
        ready      = result.get("ready_to_submit", False)
        if detected_lang := result.get("language"):
            session.language = detected_lang
        current = session.extracted_data or {}
        for k, v in extracted.items():
            if v is not None and v != "null":
                current[k] = v
        current["confidence"] = confidence
        session.extracted_data = current
        session.add_turn("assistant", reply)
        await self.repo.save(session)
        submitted = False
        if (ready or confidence >= 0.80) and session.project_id and not session.feedback_id:
            submitted = await self._auto_submit(session)
        if session.turn_count >= MAX_TURNS and not session.feedback_id:
            submitted = await self._auto_submit(session)
        await self.db.commit()
        return reply, submitted

    async def _auto_submit(self, session: ChannelSession) -> bool:
        data = session.extracted_data or {}
        if not session.project_id:
            return False
        try:
            fb_type = FeedbackType(data.get("feedback_type", "grievance"))
        except ValueError:
            fb_type = FeedbackType.GRIEVANCE

        category_def_id = None
        if slug := data.get("category_slug"):
            active_cats = await self.repo.list_active_categories(session.project_id)
            for cat in active_cats:
                if cat.slug == slug:
                    category_def_id = cat.id
                    break

        count  = await self.repo.count_feedback_for_project(session.project_id)
        prefix = {"grievance": "GRV", "suggestion": "SGG", "applause": "APP", "inquiry": "INQ"}.get(fb_type.value, "GRV")
        unique_ref = f"{prefix}-{datetime.now().year}-{count + 1:04d}"
        is_anon    = bool(data.get("is_anonymous", True))

        fb = Feedback(
            unique_ref                  = unique_ref,
            project_id                  = session.project_id,
            feedback_type               = fb_type,
            category                    = FeedbackCategory.OTHER,
            category_def_id             = category_def_id,
            status                      = FeedbackStatus.SUBMITTED,
            priority                    = FeedbackPriority.LOW,
            current_level               = GRMLevel.WARD,
            channel                     = session.channel,
            submission_method           = SubmissionMethod.AI_CONVERSATION,
            channel_session_id          = None if is_anon else session.id,
            is_anonymous                = is_anon,
            subject                     = data.get("subject") or "Feedback via " + session.channel.value,
            description                 = data.get("description") or "(Collected via conversation)",
            issue_lga                   = data.get("lga"),
            issue_ward                  = data.get("ward"),
            submitted_by_user_id        = None if is_anon else session.user_id,
            submitted_by_stakeholder_id = None if is_anon else session.stakeholder_id,
            submitted_by_contact_id     = None if is_anon else session.contact_id,
            entered_by_user_id          = session.recorded_by_user_id if (not is_anon and session.is_officer_assisted) else None,
        )
        fb = await self.fb_repo.create(fb)

        session.feedback_id  = fb.id
        session.status       = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        await self.repo.save(session)

        log.info("channel.session.auto_submitted",
                 session_id=str(session.id), feedback_id=str(fb.id), ref=unique_ref)
        return True

    async def _call_llm(
        self, session: ChannelSession, active_categories: list
    ) -> dict:
        system   = _SYSTEM_PROMPT_SW if session.language == "sw" else _SYSTEM_PROMPT_EN
        cat_list = "\n".join(f"- {c.slug}: {c.name}" for c in active_categories
                             if c.status == CategoryStatus.ACTIVE)
        if cat_list:
            system += f"\n\nAvailable categories:\n{cat_list}"
        messages = [{"role": t["role"], "content": t["content"]} for t in session.get_turns()]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if settings.ANTHROPIC_API_KEY:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "Content-Type": "application/json",
                            "x-api-key": settings.ANTHROPIC_API_KEY,
                            "anthropic-version": "2023-06-01",
                        },
                        json={"model": "claude-sonnet-4-6", "max_tokens": 600,
                              "system": system, "messages": messages},
                    )
                    text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
                else:
                    # Fallback to Groq (OpenAI-compatible)
                    groq_messages = [{"role": "system", "content": system}] + messages
                    resp = await client.post(
                        f"{settings.GROQ_BASE_URL}/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        },
                        json={"model": settings.GROQ_MODEL, "max_tokens": 600,
                              "messages": groq_messages, "temperature": 0.3,
                              "response_format": {"type": "json_object"}},
                    )
                    text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return _json.loads(text.strip())
        except Exception as exc:
            log.error("channel.llm_call_failed", session_id=str(session.id), error=str(exc))
            fallback = (
                "Samahani, kuna tatizo la kiufundi. Tafadhali jaribu tena baadaye."
                if session.language == "sw"
                else "Sorry, there was a technical issue. Please try again later."
            )
            return {"reply": fallback, "extracted": {}, "confidence": 0.0,
                    "ready_to_submit": False, "language": session.language}

    async def _register_with_auth(
        self, phone: str, channel: str, language: str
    ) -> Optional[uuid.UUID]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/auth/channel-register",
                    headers={"Content-Type": "application/json",
                             "X-Service-Key": settings.INTERNAL_SERVICE_KEY},
                    json={"phone_number": phone, "channel": channel, "language": language},
                )
                if resp.status_code == 200:
                    return uuid.UUID(resp.json()["user_id"])
        except Exception as exc:
            log.warning("channel.auth_register_failed", phone=phone, error=str(exc))
        return None

    @staticmethod
    def _detect_language(text: str) -> str:
        sw_keywords = {"habari", "malalamiko", "tatizo", "mradi", "tafadhali",
                       "nina", "kwa", "ya", "na", "au", "ni"}
        return "sw" if set(text.lower().split()) & sw_keywords else "en"
