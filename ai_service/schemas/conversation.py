"""schemas/conversation.py — Request/response schemas for ai_service."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Inbound ───────────────────────────────────────────────────────────────────

class StartConversation(BaseModel):
    """Start a new AI conversation via web or mobile app."""
    channel: str = Field(
        default="web",
        description="web | mobile",
    )
    language: str = Field(
        default="sw",
        description="Preferred language: 'sw' (Swahili) or 'en' (English)",
    )
    org_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Organisation UUID — locks the conversation to this org's projects/categories.",
    )
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Pre-select a project (e.g., from a project page). Omit to let AI detect.",
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Authenticated user ID (from JWT). If provided, the Consumer is auto-identified.",
    )
    web_token: Optional[str] = Field(
        default=None,
        description="Anonymous session token for web (used when no user_id).",
    )


class SendMessage(BaseModel):
    """Send a message in an existing conversation."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The Consumer's message text.",
    )
    media_urls: Optional[List[str]] = Field(
        default=None,
        description="Optional image/document URLs attached to this message (WhatsApp proof images).",
    )


# ── Outbound ──────────────────────────────────────────────────────────────────

class FeedbackSubmitted(BaseModel):
    feedback_id: str
    unique_ref:  str
    feedback_type: str


class ConversationResponse(BaseModel):
    """Returned after starting or sending a message."""
    conversation_id: uuid.UUID
    reply:           str
    status:          str
    stage:           str
    turn_count:      int
    confidence:      float
    language:        str
    submitted:       bool = False
    submitted_feedback: List[FeedbackSubmitted] = []
    project_name:    Optional[str] = None
    is_urgent:       bool = False
    incharge_name:   Optional[str] = None
    incharge_phone:  Optional[str] = None


class ConversationDetail(BaseModel):
    """Full conversation detail including transcript."""
    conversation_id: uuid.UUID
    channel:         str
    status:          str
    stage:           str
    language:        str
    turn_count:      int
    confidence:      float
    is_registered:   bool
    submitter_name:  Optional[str]
    project_id:      Optional[uuid.UUID]
    project_name:    Optional[str]
    extracted_data:  Dict[str, Any]
    submitted_feedback: List[Dict[str, Any]]
    transcript:      List[Dict[str, Any]]
    is_urgent:       bool
    incharge_name:   Optional[str]
    incharge_phone:  Optional[str]
    started_at:      str
    last_active_at:  str
    completed_at:    Optional[str]
