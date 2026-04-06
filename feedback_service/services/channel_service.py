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

_SYSTEM_PROMPT_SW = """Wewe ni msaidizi wa mfumo wa malalamiko wa mradi (GRM - Grievance Redress Mechanism).
Jina lako ni Riviwa. Unasaidia watu wanaotaka kuwasilisha malalamiko, maoni, au pongezi kuhusu mradi.

Lengo lako ni kukusanya taarifa zifuatazo kwa mazungumzo ya kirafiki:
1. Aina ya ujumbe (malalamiko / pendekezo / pongezi)
2. Muhtasari mfupi wa tatizo au maoni
3. Maelezo kamili
4. Eneo (LGA / Kata)
5. Tarehe ya tukio (kama inahusiana na malalamiko)
6. Jina (hiari - wanaweza kubaki wasio na jina)

Kanuni:
- Uliza maswali mawili kwa wakati mmoja kwa upole
- Unapopata taarifa za kutosha (confidence ≥ 0.80), toa muhtasari na uomba uthibitisho
- Jibu kwa Kiswahili isipokuwa mtumiaji aandike kwa Kiingereza
- Baada ya kupata uthibitisho, toa nambari ya rejeleo (itatolewa na mfumo)

Baada ya kila ujumbe wa mtumiaji, rudisha JSON hii TU (bila maelezo mengine):
{
  "reply": "<jibu lako kwa mtumiaji>",
  "extracted": {
    "feedback_type": "grievance|suggestion|applause|null",
    "subject": "<muhtasari au null>",
    "description": "<maelezo kamili au null>",
    "category_slug": "<slug kutoka orodha au null>",
    "lga": "<LGA au null>",
    "ward": "<kata au null>",
    "incident_date": "<YYYY-MM-DD au null>",
    "submitter_name": "<jina au null>",
    "is_anonymous": true|false
  },
  "confidence": 0.0,
  "ready_to_submit": false,
  "language": "sw|en"
}"""

_SYSTEM_PROMPT_EN = """You are a GRM (Grievance Redress Mechanism) assistant for an infrastructure project.
Your name is Riviwa. You help people submit grievances, suggestions, or praise about the project.

Your goal is to collect the following through friendly conversation:
1. Type of feedback (grievance / suggestion / applause)
2. Brief subject
3. Full description
4. Location (LGA / Ward)
5. Date of incident (for grievances)
6. Name (optional — they may remain anonymous)

Rules:
- Ask at most two questions at a time, politely
- When you have enough information (confidence ≥ 0.80), summarise and ask for confirmation
- Reply in the same language the user writes in

After each user message, return ONLY this JSON (no other text):
{
  "reply": "<your reply to the user>",
  "extracted": {
    "feedback_type": "grievance|suggestion|applause|null",
    "subject": "<summary or null>",
    "description": "<full description or null>",
    "category_slug": "<slug from list or null>",
    "lga": "<LGA or null>",
    "ward": "<ward or null>",
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
            project_id          = uuid.UUID(data["project_id"]) if data.get("project_id") else None,
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
            "Habari! Mimi ni Riviwa, msaidizi wa mfumo wa malalamiko. "
            "Naweza kukusaidia kuwasilisha malalamiko, maoni, au pongezi kuhusu mradi. "
            "Tafadhali niambie tatizo lako au swali lako."
        ) if session.language == "sw" else (
            "Hello! I'm Riviwa, your GRM assistant. "
            "I can help you submit a grievance, suggestion, or applause about the project. "
            "Please tell me what's on your mind."
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
                "Habari! Mimi ni Riviwa. Ninaweza kukusaidia kuwasilisha malalamiko au maoni kuhusu mradi. "
                "Tafadhali niambie tatizo lako."
            ) if lang == "sw" else (
                "Hello! I'm Riviwa. I can help you submit a grievance or feedback about the project. "
                "Please tell me what's on your mind."
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
        prefix = {"grievance": "GRV", "suggestion": "SGG", "applause": "APP"}.get(fb_type.value, "GRV")
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
