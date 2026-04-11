"""models/conversation.py — AI conversation and knowledge base models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class ConversationChannel(str, Enum):
    SMS          = "sms"
    WHATSAPP     = "whatsapp"
    PHONE_CALL   = "phone_call"
    WEB          = "web"
    MOBILE       = "mobile"


class ConversationStatus(str, Enum):
    ACTIVE     = "active"      # conversation in progress
    CONFIRMING = "confirming"  # showing summary, awaiting PAP confirmation
    SUBMITTED  = "submitted"   # all feedback submitted
    FOLLOWUP   = "followup"    # PAP is checking status of existing feedback
    ABANDONED  = "abandoned"
    TIMED_OUT  = "timed_out"
    FAILED     = "failed"


class ConversationStage(str, Enum):
    GREETING    = "greeting"    # welcome + language detection
    IDENTIFY    = "identify"    # check if registered; collect name if not
    COLLECTING  = "collecting"  # gathering feedback fields
    CLARIFYING  = "clarifying"  # asking for missing / unclear information
    CONFIRMING  = "confirming"  # showing summary, asking for confirmation
    FOLLOWUP    = "followup"    # status lookup for existing feedback
    DONE        = "done"        # terminal: submitted or abandoned


# ── Models ────────────────────────────────────────────────────────────────────

class AIConversation(SQLModel, table=True):
    """
    One row per PAP conversation session.
    Stores the full turn history and progressively extracted feedback fields.
    """
    __tablename__ = "ai_conversations"

    id:         uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    channel:    ConversationChannel = Field(index=True)
    status:     ConversationStatus  = Field(default=ConversationStatus.ACTIVE, index=True)
    stage:      ConversationStage   = Field(default=ConversationStage.GREETING)
    language:   str = Field(default="sw", max_length=10)  # "sw" or "en"

    # ── PAP identity ──────────────────────────────────────────────────────────
    phone_number:  Optional[str]      = Field(default=None, max_length=30, index=True)
    whatsapp_id:   Optional[str]      = Field(default=None, max_length=100, index=True)
    web_token:     Optional[str]      = Field(default=None, max_length=200, index=True)
    user_id:       Optional[uuid.UUID] = Field(default=None, index=True)
    is_registered: bool = Field(default=False)
    submitter_name: Optional[str] = Field(default=None, max_length=200)

    # ── Conversation state ────────────────────────────────────────────────────
    turn_count: int = Field(default=0)
    # JSONB: list of {role, content, timestamp}
    turns: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    # JSONB: progressively filled feedback fields (see ConversationService for schema)
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    # JSONB: list of submitted feedback UUIDs and their reference numbers
    submitted_feedback: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB))

    # ── Project context (auto-detected via RAG) ───────────────────────────────
    project_id:   Optional[uuid.UUID] = Field(default=None)
    project_name: Optional[str]       = Field(default=None, max_length=300)

    # ── Escalation / urgency ─────────────────────────────────────────────────
    is_urgent:      bool = Field(default=False)
    incharge_name:  Optional[str] = Field(default=None, max_length=200)
    incharge_phone: Optional[str] = Field(default=None, max_length=30)

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at:     datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at:   Optional[datetime] = Field(default=None)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def get_turns(self) -> list:
        if isinstance(self.turns, dict) and "turns" in self.turns:
            return self.turns["turns"]
        if isinstance(self.turns, list):
            return self.turns
        return []

    def add_turn(self, role: str, content: str) -> None:
        existing = self.get_turns()
        existing.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.turns = {"turns": existing}
        self.turn_count = len(existing)
        self.last_active_at = datetime.utcnow()

    def get_extracted(self) -> dict:
        if isinstance(self.extracted_data, dict):
            return self.extracted_data
        return {}

    def merge_extracted(self, new_fields: dict) -> None:
        current = self.get_extracted()
        current.update({k: v for k, v in new_fields.items() if v is not None})
        self.extracted_data = current

    def get_submitted(self) -> list:
        if isinstance(self.submitted_feedback, list):
            return self.submitted_feedback
        return []


class ProjectKnowledgeBase(SQLModel, table=True):
    """
    Local mirror of project data consumed from Kafka.
    Used for RAG project identification and context building.
    """
    __tablename__ = "ai_project_kb"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id:      uuid.UUID = Field(unique=True, index=True)
    organisation_id: uuid.UUID = Field(index=True)
    name:            str       = Field(max_length=300)
    slug:            str       = Field(max_length=200)
    description:     Optional[str] = Field(default=None, sa_column=Column(Text))
    region:          Optional[str] = Field(default=None, max_length=100)
    primary_lga:     Optional[str] = Field(default=None, max_length=100)
    # JSONB: list of ward names
    wards:           Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    # JSONB: list of keyword strings for matching
    keywords:        Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    active_stage_name: Optional[str] = Field(default=None, max_length=200)
    status:          str = Field(default="active", max_length=30)  # active|paused|completed|cancelled
    accepts_grievances:  bool = Field(default=True)
    accepts_suggestions: bool = Field(default=True)
    accepts_applause:    bool = Field(default=True)
    # Flag that this project is indexed in Qdrant vector store
    vector_indexed:  bool = Field(default=False)
    synced_at:       datetime = Field(default_factory=datetime.utcnow)

    def get_wards(self) -> list:
        if isinstance(self.wards, dict):
            return self.wards.get("wards", [])
        return []

    def get_keywords(self) -> list:
        if isinstance(self.keywords, dict):
            return self.keywords.get("keywords", [])
        return []

    def get_searchable_text(self) -> str:
        """Combine all textual fields for embedding."""
        parts = [self.name]
        if self.description:
            parts.append(self.description)
        if self.region:
            parts.append(self.region)
        if self.primary_lga:
            parts.append(self.primary_lga)
        parts.extend(self.get_wards())
        parts.extend(self.get_keywords())
        return " ".join(parts)


class StakeholderCache(SQLModel, table=True):
    """
    Cached stakeholder data from stakeholder_service (consumed via Kafka).
    Used for urgency escalation — to look up the project incharge contact.
    """
    __tablename__ = "ai_stakeholder_cache"

    id:             uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    stakeholder_id: uuid.UUID = Field(unique=True, index=True)
    project_id:     Optional[uuid.UUID] = Field(default=None, index=True)
    organisation_id: Optional[uuid.UUID] = Field(default=None, index=True)
    name:           str = Field(max_length=300)
    phone:          Optional[str] = Field(default=None, max_length=30)
    email:          Optional[str] = Field(default=None, max_length=200)
    role:           Optional[str] = Field(default=None, max_length=100)
    # True if this stakeholder is the project officer/PIU incharge
    is_incharge:    bool = Field(default=False, index=True)
    lga:            Optional[str] = Field(default=None, max_length=100)
    synced_at:      datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
