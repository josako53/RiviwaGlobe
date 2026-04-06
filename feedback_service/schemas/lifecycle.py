"""schemas/lifecycle.py — Pydantic schemas for feedback lifecycle actions."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AcknowledgeFeedback(BaseModel):
    """Acknowledge receipt of a feedback submission."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "priority": "high",
        "target_resolution_date": "2026-05-15",
        "notes": "Assigned to field team for site inspection",
    }})
    priority: Optional[str] = Field(default=None, description="Re-triage priority: critical | high | medium | low")
    target_resolution_date: Optional[str] = Field(default=None, description="Target date to resolve (YYYY-MM-DD)")
    notes: Optional[str] = Field(default=None, description="Internal acknowledgement notes")


class AssignFeedback(BaseModel):
    """Assign a feedback item to a staff member or GHC committee."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "assigned_to_user_id": "7caa7de5-a260-43f8-9da1-30bc907be8ef",
        "assigned_committee_id": None,
        "notes": "Assigned to site engineer for investigation",
    }})
    assigned_to_user_id: Optional[uuid.UUID] = Field(default=None, description="Staff member User ID to assign to")
    assigned_committee_id: Optional[uuid.UUID] = Field(default=None, description="GHC Committee ID to assign to")
    notes: Optional[str] = Field(default=None, description="Assignment notes")


class EscalateFeedback(BaseModel):
    """Escalate a grievance to the next GRM level."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "to_level": "lga_piu",
        "reason": "Ward-level GHC unable to resolve within 30 days. PAP requires LGA intervention.",
    }})
    to_level: str = Field(
        ...,
        description="Target GRM level: ward, lga_piu, pcu, tarura_wbcu, tanroads, world_bank",
        json_schema_extra={"enum": ["ward", "lga_piu", "pcu", "tarura_wbcu", "tanroads", "world_bank"]},
    )
    reason: str = Field(..., min_length=10, description="Documented reason for escalation (required for audit)")
    escalated_to_committee_id: Optional[uuid.UUID] = Field(default=None, description="GHC at the target level")


class ResolveFeedback(BaseModel):
    """Record resolution of a feedback item."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "resolution_summary": "Compensation re-assessed at market rate. PAP agrees to new valuation of TZS 45M.",
        "response_method": "in_person_meeting",
        "grievant_satisfied": True,
        "grievant_response": "PAP accepted the revised compensation amount.",
    }})
    resolution_summary: str = Field(..., min_length=10, description="Summary of how the issue was resolved")
    response_method: Optional[str] = Field(
        default=None,
        description="How the response was delivered: verbal, written_letter, email, sms, phone_call, in_person_meeting, notice_board, other",
    )
    grievant_satisfied: Optional[bool] = Field(default=None, description="Did the grievant accept the resolution?")
    grievant_response: Optional[str] = Field(default=None, description="Grievant's response to the proposed resolution")
    witness_name: Optional[str] = Field(default=None, description="Witness name (Annex 5: Grievant/LGA Representative Signature)")


class AppealFeedback(BaseModel):
    """File an appeal against a resolution."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "appeal_grounds": "The revised compensation still does not reflect current market rates for commercial land in Ilala.",
    }})
    appeal_grounds: str = Field(..., min_length=10, description="Reason for appealing the resolution")


class CloseFeedback(BaseModel):
    """Close a feedback item (final state)."""
    model_config = ConfigDict(json_schema_extra={"example": {"notes": "PAP confirmed satisfaction. Case closed."}})
    notes: Optional[str] = Field(default=None, description="Closing notes")


class DismissFeedback(BaseModel):
    """Dismiss a feedback item as unfounded, duplicate, or out of scope."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "reason": "Duplicate of GRV-2026-0003. Same issue reported by same PAP.",
    }})
    reason: str = Field(..., min_length=5, description="Reason for dismissal (required for audit)")


class LogAction(BaseModel):
    """Log an action taken on a feedback item."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "action_type": "site_visit",
        "description": "Visited the construction site to assess dust levels and spoke with contractor.",
        "response_method": "verbal",
        "response_summary": "Contractor agreed to water the road twice daily to suppress dust.",
    }})
    action_type: str = Field(
        ...,
        description=(
            "Type of action: acknowledgement, investigation, site_visit, stakeholder_meeting, "
            "internal_review, response, escalation_note, resolution_draft, appeal_review, note"
        ),
    )
    description: str = Field(..., min_length=5, description="What was done")
    is_internal: bool = Field(default=False, description="True = staff-only note, not visible to PAP")
    response_method: Optional[str] = Field(default=None, description="How response was delivered (if applicable)")
    response_summary: Optional[str] = Field(default=None, description="Summary of the response given")


class PAPEscalationRequest(BaseModel):
    """PAP requests escalation of their grievance."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "reason": "No response after 30 days despite multiple follow-ups",
        "requested_level": "lga_piu",
    }})
    reason: str = Field(..., min_length=10, description="Why you want your case escalated")
    requested_level: Optional[str] = Field(default=None, description="Requested GRM level (optional — PIU decides)")


class PAPAppeal(BaseModel):
    """PAP files a formal appeal against an unsatisfactory resolution."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "grounds": "Resolution does not address the core issue of fair compensation for my land.",
    }})
    grounds: str = Field(..., min_length=10, description="Grounds for your appeal")


class PAPComment(BaseModel):
    """PAP adds a follow-up comment to their submission."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "comment": "I have new photographs showing the damage from last week's construction activity.",
    }})
    comment: str = Field(..., min_length=5, max_length=2000, description="Your follow-up comment or additional information")


class ApproveEscalation(BaseModel):
    """Staff approves a PAP's escalation request."""
    model_config = ConfigDict(json_schema_extra={"example": {"notes": "Justified — unresolved for 45 days."}})
    notes: Optional[str] = Field(default=None, description="Approval notes")


class RejectEscalation(BaseModel):
    """Staff rejects a PAP's escalation request with explanation."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "notes": "Case is being actively investigated. Resolution expected within 7 days.",
    }})
    notes: str = Field(..., min_length=5, description="Reason for rejection (visible to PAP)")
