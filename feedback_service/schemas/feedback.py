"""
schemas/feedback.py — Pydantic request/response schemas for feedback submission.

Four submission paths:
  1. Consumer self-service: POST /api/v1/my/feedback         → ConsumerSubmitFeedback
  2. Staff/officer:         POST /api/v1/feedback             → StaffSubmitFeedback
  3. Staff bulk:            POST /api/v1/feedback/bulk-upload  → CSV file
  4. AI/ML channel:         POST /api/v1/ai/sessions           → AIChannelSessionCreate

Consumer: project_id optional (ML auto-assigns), channel auto-detected, priority=medium.
Staff: full control — can set project_id, backdate, set priority, GPS, etc.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ══════════════════════════════════════════════════════════════════════════════
# CONSUMER / END-USER SUBMISSION (simplified)
# POST /api/v1/my/feedback
# ══════════════════════════════════════════════════════════════════════════════

class ConsumerSubmitFeedback(BaseModel):
    """
    Simplified feedback submission for Consumers.

    project_id and category are optional — AI auto-detects them from your
    description and location (issue_lga is required to enable detection).

    If the AI cannot identify a unique project, the API returns HTTP 422
    with a `candidate_projects` list so the frontend can show a picker
    and re-submit with the chosen project_id.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "feedback_type": "grievance",
            "description": "Since Monday the construction crew has blocked the only road to my shop. I am losing customers every day.",
            "submitter_name": "Juma Bakari",
            "submitter_phone": "+255787654321",
            "issue_lga": "Ilala",
            "issue_ward": "Kariakoo",
            "issue_location_description": "Near Kariakoo market, next to the blue gate",
            "date_of_incident": "2026-04-01",
        }
    })

    # ── Required ──────────────────────────────────────────────────────────────
    feedback_type: str = Field(
        ...,
        description="grievance | suggestion | applause",
        json_schema_extra={"enum": ["grievance", "suggestion", "applause"]},
    )
    description: str = Field(
        ..., min_length=10,
        description="What happened — the more detail you give, the better the AI can identify the project.",
    )
    issue_lga: str = Field(
        ..., min_length=2,
        description="District / LGA where the issue occurred. Required so the AI can identify the relevant project.",
    )

    # ── AI auto-detected if omitted ───────────────────────────────────────────
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Project UUID. Omit to let the AI detect it from your location and description.",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category slug. Omit to let the AI classify from your description.",
    )
    subject: Optional[str] = Field(
        default=None, max_length=500,
        description="Short summary. Auto-generated from description if omitted.",
    )

    # ── Submitter identity ────────────────────────────────────────────────────
    is_anonymous: bool = Field(default=False, description="Submit anonymously")
    submitter_name: Optional[str] = Field(default=None, max_length=255)
    submitter_phone: Optional[str] = Field(default=None, max_length=20)

    # ── Issue location ────────────────────────────────────────────────────────
    issue_ward: Optional[str] = Field(default=None, description="Ward where the issue occurred")
    issue_location_description: Optional[str] = Field(
        default=None,
        description="Free-text location description — landmark, road name, village, etc.",
    )
    issue_gps_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    issue_gps_lng: Optional[float] = Field(default=None, ge=-180, le=180)

    # ── Sub-project link ──────────────────────────────────────────────────────
    subproject_id: Optional[uuid.UUID] = Field(default=None, description="Sub-project (work package) UUID")

    # ── Department link ───────────────────────────────────────────────────────
    department_id: Optional[uuid.UUID] = Field(
        default=None,
        description="OrgDepartment UUID — which department this feedback is directed at (e.g. HR, Finance).",
    )

    # ── Date and media ────────────────────────────────────────────────────────
    date_of_incident: Optional[str] = Field(default=None, description="When the issue happened (YYYY-MM-DD)")
    media_urls: Optional[List[str]] = Field(default=None, description="Photo/video URLs")



# ══════════════════════════════════════════════════════════════════════════════
# STAFF / OFFICER SUBMISSION (full Annex 5 + digital extensions)
# POST /api/v1/feedback
# ══════════════════════════════════════════════════════════════════════════════

class StaffSubmitFeedback(BaseModel):
    """
    Full feedback submission by GHC/GRM Unit staff or officer.
    Covers all Annex 5 fields + digital extensions.
    Staff can backdate, set project_id, priority, GPS, etc.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "feedback_type": "grievance",
            "category": "compensation",
            "channel": "paper_form",
            "subject": "Unfair compensation for land acquisition",
            "description": "Consumer claims the compensation offered for 2 acres is below market rate. Land was acquired on 15 Sep 2025.",
            "submitter_name": "Amina Hassan",
            "submitter_phone": "+255712345678",
            "submitter_type": "individual",
            "issue_lga": "Ilala",
            "issue_ward": "Kariakoo",
            "date_of_incident": "2025-09-15",
            "submitted_at": "2025-10-01",
            "priority": "high",
            "officer_recorded": True,
            "internal_notes": "Consumer has supporting documents. Scheduled for valuation review.",
        }
    })

    # ── SECTION A — Required ──────────────────────────────────────────────────
    project_id: uuid.UUID = Field(..., description="Project UUID (Annex 5: Type of activity under MVDP)")
    feedback_type: str = Field(
        ...,
        description="grievance | suggestion | applause",
        json_schema_extra={"enum": ["grievance", "suggestion", "applause"]},
    )
    category: str = Field(..., description="Feedback category (Annex 5: Type of Complaint)")
    channel: str = Field(
        ...,
        description=(
            "How feedback arrived (Annex 5: Verbal/Telephone/Written). "
            "sms, whatsapp, phone_call, mobile_app, web_portal, in_person, "
            "paper_form, email, public_meeting, notice_box, other"
        ),
    )
    subject: str = Field(..., min_length=5, max_length=500, description="Short summary (Annex 5: Complaint header)")
    description: str = Field(..., min_length=10, description="Full description (Annex 5: Complaint Description)")

    # ── SECTION B — Submitter / Grievant Identity (Annex 5) ───────────────────
    is_anonymous: bool = Field(default=False, description="CONFIDENTIAL submission")
    submitter_name: Optional[str] = Field(default=None, max_length=255, description="Grievant Name")
    submitter_phone: Optional[str] = Field(default=None, max_length=20, description="Contact — phone (E.164)")
    submitter_email: Optional[str] = Field(default=None, max_length=255, description="Contact — email")
    submitter_type: Optional[str] = Field(
        default="individual",
        description="individual | group | community_organisation (Annex 5 checkbox)",
    )
    group_size: Optional[int] = Field(default=None, description="Number of affected persons if group")
    submitter_location_region: Optional[str] = Field(default=None, description="Grievant address — region")
    submitter_location_district: Optional[str] = Field(default=None, description="Grievant address — district")
    submitter_location_lga: Optional[str] = Field(default=None, description="Grievant address — LGA")
    submitter_location_ward: Optional[str] = Field(default=None, description="Grievant address — ward")
    submitter_location_street: Optional[str] = Field(default=None, description="Grievant address — street/plot")
    submitted_by_user_id: Optional[uuid.UUID] = Field(default=None, description="Riviwa User ID")
    submitted_by_stakeholder_id: Optional[uuid.UUID] = Field(default=None, description="Stakeholder ID")
    submitted_by_contact_id: Optional[uuid.UUID] = Field(default=None, description="StakeholderContact ID")

    # ── SECTION C — Triage (Annex 5: Action Officer) ──────────────────────────
    priority: str = Field(
        default="medium",
        description="critical | high | medium | low",
        json_schema_extra={"enum": ["critical", "high", "medium", "low"]},
    )

    # ── SECTION D — Issue Location (Annex 6) ──────────────────────────────────
    issue_location_description: Optional[str] = Field(default=None, max_length=500, description="Free-text location")
    issue_region: Optional[str] = Field(default=None, description="Region where issue occurred")
    issue_district: Optional[str] = Field(default=None, description="District")
    issue_lga: Optional[str] = Field(default=None, description="LGA / Municipal")
    issue_ward: Optional[str] = Field(default=None, description="Ward")
    issue_mtaa: Optional[str] = Field(default=None, description="Mtaa / sub-ward")
    issue_gps_lat: Optional[float] = Field(default=None, ge=-90, le=90, description="GPS latitude")
    issue_gps_lng: Optional[float] = Field(default=None, ge=-180, le=180, description="GPS longitude")

    # ── SECTION E — Dates (Annex 5: Date of Action Causing Complaint) ─────────
    date_of_incident: Optional[str] = Field(default=None, description="When the issue happened (YYYY-MM-DD)")
    submitted_at: Optional[str] = Field(
        default=None,
        description="Backdate: override submission date (YYYY-MM-DD or ISO). Defaults to now.",
    )

    # ── SECTION F — Evidence ──────────────────────────────────────────────────
    media_urls: Optional[List[str]] = Field(default=None, description="Photos, scanned documents (URLs)")

    # ── SECTION G — Cross-references ──────────────────────────────────────────
    subproject_id: Optional[uuid.UUID] = Field(default=None, description="Sub-project (work package) this feedback relates to")
    department_id: Optional[uuid.UUID] = Field(
        default=None,
        description="OrgDepartment UUID — which department this feedback is directed at (e.g. HR, Finance, Customer Care).",
    )
    service_location_id: Optional[uuid.UUID] = Field(default=None)
    stakeholder_engagement_id: Optional[uuid.UUID] = Field(default=None, description="From public meeting (Annex 5)")
    distribution_id: Optional[uuid.UUID] = Field(default=None)

    # ── SECTION H — Officer metadata (Annex 5: Action Officer from LGA) ──────
    officer_recorded: bool = Field(default=False, description="Staff entered on behalf of Consumer")
    internal_notes: Optional[str] = Field(default=None, description="Internal GRM Unit notes (Annex 5: Response/Follow up)")



# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class FeedbackSubmitResponse(BaseModel):
    """Returned after successful feedback submission."""
    feedback_id: uuid.UUID = Field(description="Unique database ID")
    tracking_number: str = Field(description="Human-readable reference (e.g. GRV-2026-0001)")
    status: str = Field(description="Current status: submitted")
    feedback_type: str
    message: str = Field(description="Confirmation message for the user")


# ══════════════════════════════════════════════════════════════════════════════
# BULK UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

class BulkUploadResult(BaseModel):
    """Result of a bulk feedback upload."""
    total_rows: int = Field(description="Total rows in the uploaded file")
    created: int = Field(description="Rows successfully imported")
    skipped: int = Field(description="Rows skipped (validation errors)")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Per-row errors: [{row: 3, field: 'feedback_type', error: 'invalid value'}]",
    )


# ══════════════════════════════════════════════════════════════════════════════
# AI / ML CHANNEL SESSION (automated SMS/WhatsApp/Call)
# ══════════════════════════════════════════════════════════════════════════════

class AIChannelSessionCreate(BaseModel):
    """Start an AI-powered conversation session."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "channel": "whatsapp",
            "phone_number": "+255712345678",
            "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "language": "sw",
        }
    })

    channel: str = Field(..., description="sms | whatsapp | phone_call")
    phone_number: Optional[str] = Field(default=None, max_length=20)
    whatsapp_id: Optional[str] = Field(default=None, max_length=50)
    project_id: Optional[uuid.UUID] = Field(default=None, description="Auto-detected if omitted")
    language: str = Field(default="sw", description="sw | en")
    gateway_session_id: Optional[str] = Field(default=None)
    gateway_provider: str = Field(default="other")


class AIChannelMessage(BaseModel):
    """Send a message in an active AI conversation."""
    model_config = ConfigDict(json_schema_extra={
        "example": {"message": "Nina malalamiko kuhusu vumbi kutoka ujenzi karibu na nyumba yangu"}
    })
    message: str = Field(..., min_length=1, max_length=2000)


class AISessionResponse(BaseModel):
    """Response from the AI conversation engine."""
    session_id: uuid.UUID
    reply: str
    submitted: bool = False
    feedback_id: Optional[uuid.UUID] = None
    tracking_number: Optional[str] = None
    status: str
    turn_count: int
    confidence: float = 0.0
    language: str = "sw"
