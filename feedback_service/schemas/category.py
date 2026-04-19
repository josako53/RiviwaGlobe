"""schemas/category.py — Pydantic schemas for category and channel-session endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

class CreateCategory(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Display name e.g. 'Water supply'")
    slug: Optional[str] = Field(
        default=None, max_length=80,
        description="URL-safe identifier e.g. 'water-supply'. Auto-generated from name if omitted.",
    )
    description: Optional[str] = Field(default=None, description="Longer explanation of what belongs in this category")
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Scope to a specific project. Omit for a platform-wide category visible to all projects.",
    )
    applicable_types: Optional[List[str]] = Field(
        default=["grievance", "suggestion", "applause"],
        description="Which feedback types this category applies to: grievance | suggestion | applause",
    )
    color_hex: Optional[str] = Field(default=None, max_length=7, description="Hex colour for UI badge e.g. '#E24B4A'")
    icon: Optional[str] = Field(default=None, max_length=50, description="Icon identifier e.g. 'water-drop'")
    display_order: Optional[int] = Field(default=0, description="Sort order in dropdowns (lower = first)")


class UpdateCategory(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None)
    applicable_types: Optional[List[str]] = Field(default=None)
    color_hex: Optional[str] = Field(default=None, max_length=7)
    icon: Optional[str] = Field(default=None, max_length=50)
    display_order: Optional[int] = Field(default=None)


class ApproveCategory(BaseModel):
    notes: Optional[str] = Field(default=None, description="Reviewer notes")
    name: Optional[str] = Field(default=None, description="Override the suggested name before approving")
    slug: Optional[str] = Field(default=None, description="Override the suggested slug before approving")


class RejectCategory(BaseModel):
    notes: Optional[str] = Field(default=None, description="Reason for rejection — sent back to requester")


class DeactivateCategory(BaseModel):
    notes: Optional[str] = Field(default=None, description="Reason for deactivation")


class MergeCategory(BaseModel):
    merge_into_id: uuid.UUID = Field(..., description="ID of the target category to merge into")
    notes: Optional[str] = Field(default=None, description="Reason for merge")


class ClassifyFeedback(BaseModel):
    force: bool = Field(
        default=False,
        description="Re-run ML classification even if a category is already assigned",
    )


class RecategoriseFeedback(BaseModel):
    category_def_id: uuid.UUID = Field(..., description="ID of the FeedbackCategoryDef to assign")


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL SESSION
# ══════════════════════════════════════════════════════════════════════════════

class CreateChannelSession(BaseModel):
    channel: str = Field(
        ...,
        description="sms | whatsapp | whatsapp_voice | phone_call | mobile_app | web_portal | in_person | paper_form | email | public_meeting | notice_box | other",
    )
    project_id: Optional[uuid.UUID] = Field(default=None, description="Project the session is linked to")
    phone_number: Optional[str] = Field(default=None, max_length=20, description="Consumer phone number (E.164)")
    whatsapp_id: Optional[str] = Field(default=None, max_length=100, description="WhatsApp sender ID")
    gateway_session_id: Optional[str] = Field(default=None, max_length=200, description="Gateway-assigned session ID")
    gateway_provider: Optional[str] = Field(default="other", max_length=50, description="Gateway provider name")
    language: Optional[str] = Field(default="sw", max_length=10, description="IETF language tag: 'sw' or 'en'")
    is_officer_assisted: bool = Field(
        default=False,
        description="True when a GRM Unit officer is operating on behalf of a walk-in Consumer",
    )


class AbandonSession(BaseModel):
    reason: Optional[str] = Field(default=None, description="Why the session was abandoned")
