"""
schemas/stakeholder.py — Pydantic request schemas for stakeholder_service.

Replaces the raw Dict[str, Any] bodies that caused Swagger to show
{additionalProp1: {}} and gave no validation at the API boundary.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ══════════════════════════════════════════════════════════════════════════════
# Stakeholder
# ══════════════════════════════════════════════════════════════════════════════

class RegisterStakeholder(BaseModel):
    """POST /api/v1/stakeholders — Register a new stakeholder."""

    # ── Required ───────────────────────────────────────────────────────────────
    stakeholder_type: str = Field(
        ...,
        description="pap | interested_party",
        json_schema_extra={"enum": ["pap", "interested_party"]},
    )
    entity_type: str = Field(
        ...,
        description="individual | organization | group",
        json_schema_extra={"enum": ["individual", "organization", "group"]},
    )
    category: str = Field(
        ...,
        description=(
            "individual | local_government | national_government | ngo_cbo | "
            "community_group | private_company | utility_provider | "
            "development_partner | media | academic_research | vulnerable_group | other"
        ),
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    org_name:   Optional[str] = Field(default=None, max_length=255, description="Organisation / group name (required if entity_type is organization or group)")
    first_name: Optional[str] = Field(default=None, max_length=100, description="First name (for individuals)")
    last_name:  Optional[str] = Field(default=None, max_length=100, description="Last name (for individuals)")

    # ── Classification ─────────────────────────────────────────────────────────
    affectedness: str = Field(
        default="unknown",
        description="positively_affected | negatively_affected | both | unknown",
        json_schema_extra={"enum": ["positively_affected", "negatively_affected", "both", "unknown"]},
    )
    importance_rating: str = Field(
        default="medium",
        description="high | medium | low",
        json_schema_extra={"enum": ["high", "medium", "low"]},
    )

    # ── Location ───────────────────────────────────────────────────────────────
    lga:  Optional[str] = Field(default=None, description="Local Government Authority")
    ward: Optional[str] = Field(default=None, description="Ward")

    # ── Communication preferences ──────────────────────────────────────────────
    language_preference: str = Field(default="sw", description="Preferred language code: sw | en")
    preferred_channel: str = Field(
        default="public_meeting",
        description=(
            "public_meeting | focus_group | email | sms | phone_call | "
            "radio | tv | social_media | billboard | notice_board | letter | in_person"
        ),
    )

    # ── Access needs ───────────────────────────────────────────────────────────
    needs_translation: bool = Field(default=False, description="Requires translation services")
    needs_transport:   bool = Field(default=False, description="Requires transport to attend meetings")
    needs_childcare:   bool = Field(default=False, description="Requires childcare during meetings")

    # ── Vulnerability ──────────────────────────────────────────────────────────
    is_vulnerable: bool = Field(default=False, description="Flag as a vulnerable stakeholder")
    vulnerable_group_types: Optional[List[str]] = Field(
        default=None,
        description=(
            "Vulnerability types: children | women_low_income | disabled_physical | "
            "disabled_mental | elderly | youth | low_income | indigenous | language_barrier"
        ),
    )
    participation_barriers: Optional[str] = Field(default=None, description="Free-text description of barriers to participation")

    # ── Cross-references ───────────────────────────────────────────────────────
    org_id:     Optional[uuid.UUID] = Field(default=None, description="Riviwa organisation UUID")
    address_id: Optional[uuid.UUID] = Field(default=None, description="Address record UUID")

    # ── Notes ──────────────────────────────────────────────────────────────────
    notes: Optional[str] = Field(default=None, description="Internal PIU notes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stakeholder_type": "pap",
                "entity_type": "individual",
                "category": "individual",
                "first_name": "Juma",
                "last_name": "Bakari",
                "affectedness": "negatively_affected",
                "importance_rating": "high",
                "lga": "Ilala",
                "ward": "Kariakoo",
                "language_preference": "sw",
                "preferred_channel": "sms",
                "needs_translation": False,
                "needs_transport": False,
                "needs_childcare": False,
                "is_vulnerable": False,
            }
        }
    }


class UpdateStakeholder(BaseModel):
    """PATCH /api/v1/stakeholders/{id} — Update a stakeholder profile."""

    affectedness:      Optional[str]       = Field(default=None, description="positively_affected | negatively_affected | both | unknown")
    importance_rating: Optional[str]       = Field(default=None, description="high | medium | low")
    org_name:          Optional[str]       = Field(default=None, max_length=255)
    first_name:        Optional[str]       = Field(default=None, max_length=100)
    last_name:         Optional[str]       = Field(default=None, max_length=100)
    address_id:        Optional[uuid.UUID] = Field(default=None)
    lga:               Optional[str]       = Field(default=None)
    ward:              Optional[str]       = Field(default=None)
    language_preference: Optional[str]    = Field(default=None)
    preferred_channel: Optional[str]      = Field(default=None)
    needs_translation: Optional[bool]     = Field(default=None)
    needs_transport:   Optional[bool]     = Field(default=None)
    needs_childcare:   Optional[bool]     = Field(default=None)
    is_vulnerable:     Optional[bool]     = Field(default=None)
    vulnerable_group_types:  Optional[List[str]] = Field(default=None)
    participation_barriers:  Optional[str]       = Field(default=None)
    notes:             Optional[str]       = Field(default=None)
    logo_url:          Optional[str]       = Field(default=None, description="Pass null to clear; or a pre-existing URL")


# ══════════════════════════════════════════════════════════════════════════════
# Stakeholder ↔ Project registration
# ══════════════════════════════════════════════════════════════════════════════

class RegisterStakeholderProject(BaseModel):
    """POST /api/v1/stakeholders/{id}/projects — Register stakeholder under a project."""

    project_id:        uuid.UUID      = Field(..., description="Project UUID to register under")
    is_pap:            bool           = Field(default=False, description="Is this stakeholder a Project-Affected Person for this project?")
    affectedness:      Optional[str]  = Field(default=None, description="positively_affected | negatively_affected | both | unknown")
    impact_description: Optional[str] = Field(default=None, description="Description of how the project impacts this stakeholder")

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "is_pap": True,
                "affectedness": "negatively_affected",
                "impact_description": "Land acquisition for road widening affects 0.5 acres of farmland",
            }
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# Contacts
# ══════════════════════════════════════════════════════════════════════════════

class AddContact(BaseModel):
    """POST /api/v1/stakeholders/{id}/contacts — Add a contact person."""

    # ── Required ───────────────────────────────────────────────────────────────
    full_name: str = Field(..., max_length=255, description="Contact person's full name")

    # ── Identity ───────────────────────────────────────────────────────────────
    title:       Optional[str] = Field(default=None, max_length=100, description="e.g. Dr., Mr., Ms., Eng.")
    role_in_org: Optional[str] = Field(default=None, max_length=255, description="Their role in the organisation (e.g. Community Liaison Officer)")
    email:       Optional[str] = Field(default=None, max_length=255, description="Email address")
    phone:       Optional[str] = Field(default=None, max_length=20, description="Phone number in E.164 format (+255...)")
    user_id:     Optional[uuid.UUID] = Field(default=None, description="Link to a Riviwa user account")

    # ── Communication preferences ──────────────────────────────────────────────
    preferred_channel: str = Field(
        default="phone_call",
        description="public_meeting | focus_group | email | sms | phone_call | radio | tv | social_media | billboard | notice_board | letter | in_person",
    )

    # ── Permissions ────────────────────────────────────────────────────────────
    is_primary:                    bool = Field(default=False, description="Primary contact for the stakeholder")
    can_submit_feedback:           bool = Field(default=True,  description="Allowed to submit feedback on behalf of stakeholder")
    can_receive_communications:    bool = Field(default=True,  description="Should receive communications from PIU")
    can_distribute_communications: bool = Field(default=False, description="Can distribute communications to the wider group")

    # ── Notes ──────────────────────────────────────────────────────────────────
    notes: Optional[str] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Amina Hassan",
                "title": "Ms.",
                "role_in_org": "Community Liaison Officer",
                "email": "amina.hassan@example.com",
                "phone": "+255712345678",
                "preferred_channel": "phone_call",
                "is_primary": True,
                "can_submit_feedback": True,
                "can_receive_communications": True,
                "can_distribute_communications": False,
            }
        }
    }


class UpdateContact(BaseModel):
    """PATCH /api/v1/stakeholders/{id}/contacts/{id} — Update a contact."""

    full_name:                     Optional[str]       = Field(default=None, max_length=255)
    title:                         Optional[str]       = Field(default=None, max_length=100)
    role_in_org:                   Optional[str]       = Field(default=None, max_length=255)
    email:                         Optional[str]       = Field(default=None, max_length=255)
    phone:                         Optional[str]       = Field(default=None, max_length=20)
    preferred_channel:             Optional[str]       = Field(default=None)
    is_primary:                    Optional[bool]      = Field(default=None)
    can_submit_feedback:           Optional[bool]      = Field(default=None)
    can_receive_communications:    Optional[bool]      = Field(default=None)
    can_distribute_communications: Optional[bool]      = Field(default=None)
    notes:                         Optional[str]       = Field(default=None)
    user_id:                       Optional[uuid.UUID] = Field(default=None)


class DeactivateContact(BaseModel):
    """DELETE /api/v1/stakeholders/{id}/contacts/{id} — Deactivate a contact."""

    reason: Optional[str] = Field(default=None, description="Reason for deactivation")
