# ───────────────────────────────────────────────────────────────────────────
# SERVICE   :  feedback_service
# PORT      :  Port: 8090
# DATABASE  :  DB: feedback_db (5434)
# FILE      :  models/feedback.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/feedback.py
═══════════════════════════════════════════════════════════════════════════════
The complete Feedback domain — three submission types on one table,
with the GRM escalation hierarchy always present.

DESIGN PRINCIPLE: ONE TABLE, THREE TYPES
──────────────────────────────────────────────────────────────────────────────
  Feedback  → the single submission table
    · type = GRIEVANCE:  formal complaint, always routes through GRM
    · type = SUGGESTION: idea or recommendation, simpler lifecycle
    · type = APPLAUSE:   positive recognition, simplest lifecycle

  The GRM (Grievance Redress Mechanism) is ALWAYS PRESENT — every feedback
  submission has the full escalation chain available. For SUGGESTION and
  APPLAUSE this is mostly dormant (they rarely escalate), but the structure
  is consistent. This was the explicit design decision: no conditional logic
  based on type, no missing tables.

FEEDBACK LIFECYCLE
──────────────────────────────────────────────────────────────────────────────

  GRIEVANCE lifecycle (most complex):
    SUBMITTED → ACKNOWLEDGED → IN_REVIEW → [ESCALATED →] RESOLVED → CLOSED
                                          ↓
                                        APPEALED → [re-review] → RESOLVED

  SUGGESTION / APPLAUSE lifecycle (simpler):
    SUBMITTED → ACKNOWLEDGED → ACTIONED (or NOTED) → CLOSED

  DISMISSED is available for all types (unfounded, duplicate, out of scope).

GRM ESCALATION HIERARCHY (SEP Section 5)
──────────────────────────────────────────────────────────────────────────────
  Level 1  WARD          Ward/sub-project GHC — first point of contact
  Level 2  LGA_PIU       LGA Grievance Handling Committee at LGA GRM Unit level
  Level 3  PCU           Coordinating Unit (PO-RALG/TARURA)
  Level 4  TARURA_WBCU   TARURA World Bank Coordinating Unit
  Level 5  TANROADS      For bridge/road-specific grievances
  Level 6  WORLD_BANK    Final escalation — World Bank direct

  Grievances start at WARD (Level 1) by default.
  Each escalation creates a FeedbackEscalation row with from/to/reason.
  Anonymous grievances can escalate — the anonymity is preserved at each level.

ANONYMOUS SUBMISSIONS
──────────────────────────────────────────────────────────────────────────────
  Any submission type can be anonymous (is_anonymous=True).
  When anonymous:
    · submitted_by_user_id is null
    · submitted_by_stakeholder_id is null
    · submitted_by_contact_id is null
    · submitter_name / submitter_phone may or may not be provided
  The SEP explicitly requires anonymous reporting capability for GRM.

SUBMITTER IDENTITY CHAIN (three paths)
──────────────────────────────────────────────────────────────────────────────
  Path 1 — Authenticated platform user (has JWT)
    submitted_by_user_id set → look up StakeholderContact via user_id
    submitted_by_stakeholder_id / contact_id auto-populated if found

  Path 2 — Known stakeholder contact (no platform account)
    submitted_by_stakeholder_id + submitted_by_contact_id set by GRM Unit staff
    Feedback entered on the contact's behalf

  Path 3 — Anonymous / unknown individual
    All three IDs null
    submitter_name / submitter_phone optionally provided
    is_anonymous = True

CROSS-SERVICE SOFT LINKS
──────────────────────────────────────────────────────────────────────────────
  submitted_by_user_id        → auth_service User.id
  submitted_by_stakeholder_id → stakeholder_service Stakeholder.id
  submitted_by_contact_id     → stakeholder_service StakeholderContact.id
  stakeholder_engagement_id   → stakeholder_service StakeholderEngagement.id
  distribution_id             → stakeholder_service CommunicationDistribution.id

  None of these are FK constraints — all are application-layer soft links.
  Resolved via Kafka events and service-layer lookups.

TABLE INVENTORY
──────────────────────────────────────────────────────────────────────────────
  Feedback             — the unified submission record
  FeedbackAction       — every step taken: acknowledgement, investigation, response
  FeedbackEscalation   — one row per escalation event (from_level → to_level)
  FeedbackResolution   — one row per resolution (1-to-1 with Feedback)
  FeedbackAppeal       — filed when grievant is unsatisfied with resolution
  GrievanceCommittee   — GHC instances at different levels/LGAs
  GrievanceCommitteeMember — who sits on which GHC
═══════════════════════════════════════════════════════════════════════════════
"""
# from __future__ import annotations  # removed: breaks List[Model] SQLModel relationship annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

# Runtime import — SQLAlchemy mapper needs to resolve "ProjectCache"
# string in Relationship() at runtime. No circular import risk.
from models.project import ProjectCache, ProjectStageCache        # noqa: F401



class FeedbackType(str, Enum):
    """
    The spectrum of feedback that can be submitted about any project.

    GRIEVANCE   → formal complaint requiring investigation and resolution.
                  Always routes through the GRM escalation hierarchy.
                  Examples: unfair compensation, construction noise, safety hazard,
                  lack of access, worker mistreatment, environmental damage.

    SUGGESTION  → constructive idea or recommendation to improve the project.
                  Simpler lifecycle — acknowledged, considered, actioned or noted.
                  Examples: widen pedestrian path, add community notice board,
                  change meeting schedule, include women in consultation committees.

    APPLAUSE    → positive feedback recognising good performance.
                  Simplest lifecycle — acknowledged and closed.
                  Examples: bridge completed on schedule, contractor was respectful,
                  GRM Unit responded quickly to a concern, resettlement was well handled.

    INQUIRY     → question or request for information. No GRM escalation.
                  Examples: how does the compensation process work?, what is the
                  status of my land valuation?, who do I contact about X?
    """
    GRIEVANCE   = "grievance"
    SUGGESTION  = "suggestion"
    APPLAUSE    = "applause"
    INQUIRY     = "inquiry"

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class FeedbackStatus(str, Enum):
    """
    Unified status for all feedback types.
    Not all statuses apply to all types — see lifecycle notes in module docstring.
    """
    SUBMITTED    = "submitted"    # just received, not yet acknowledged
    ACKNOWLEDGED = "acknowledged" # GRM Unit/GHC confirmed receipt
    IN_REVIEW    = "in_review"    # actively being investigated
    ESCALATED    = "escalated"    # moved to higher GRM level
    RESOLVED     = "resolved"     # resolution provided to submitter
    APPEALED     = "appealed"     # grievant challenged the resolution
    ACTIONED     = "actioned"     # suggestion implemented (SUGGESTION only)
    NOTED        = "noted"        # suggestion received but not implemented (SUGGESTION only)
    DISMISSED    = "dismissed"    # found unfounded, duplicate, or out of scope
    CLOSED       = "closed"       # final state — no further action

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class FeedbackPriority(str, Enum):
    """
    GRM Unit-assigned priority for triage. Drives acknowledgement and resolution timeframes.

    CRITICAL → safety risk, legal obligation, or World Bank escalation risk.
               Acknowledge within 24 hours. Resolve within 7 days.
    HIGH     → significant impact on Consumers or project progress.
               Acknowledge within 48 hours. Resolve within 14 days.
    MEDIUM   → standard grievance or substantive suggestion.
               Acknowledge within 5 days. Resolve within 30 days.
    LOW      → minor or informational. Acknowledge within 10 days.
    """
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class GRMLevel(str, Enum):
    """
    Escalation level within the GRM hierarchy (SEP Section 5).
    Grievances start at WARD and escalate upward only.
    Each escalation requires a documented reason.
    """
    WARD             = "ward"             # Level 1 — Ward/sub-project GHC
    LGA_GRM_UNIT     = "lga_grm_unit"    # Level 2 — LGA GRM Handling Unit
    COORDINATING_UNIT = "coordinating_unit" # Level 3 — Coordinating Unit
    TARURA_WBCU      = "tarura_wbcu"     # Level 4 — TARURA World Bank Coordinating Unit
    TANROADS         = "tanroads"         # Level 5 — For road/bridge-specific escalations
    WORLD_BANK       = "world_bank"       # Level 6 — Final escalation

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class FeedbackChannel(str, Enum):
    """
    The technical channel through which the feedback entered the system.

    IMPORTANT DISTINCTION — two axes are captured separately:
      FeedbackChannel  → the MEDIUM (how it arrived: SMS, WhatsApp, mobile app…)
      SubmissionMethod → the ACTOR  (who created the record: self, officer, AI)

    This is different from the SEP procedural channels (which GRM Unit/LGA departments
    are responsible for handling). FeedbackChannel is purely about the technical
    intake path for filtering and analytics.

    Two-way AI channels (SMS, WHATSAPP, PHONE_CALL):
      The LLM conducts a structured multi-turn conversation with the Consumer to
      collect all required grievance details. Once the LLM has enough information,
      it submits the Feedback record automatically. The full conversation is stored
      in ChannelSession. These channels can also be used officer-recorded (officer
      dials on behalf of a walk-in, or types the content of a letter).

    Self-service channels (MOBILE_APP, WEB_PORTAL):
      Consumer fills in a structured form directly. No LLM conversation needed.

    Officer-recorded channels (IN_PERSON, PAPER_FORM, EMAIL, PUBLIC_MEETING,
    NOTICE_BOX): always SubmissionMethod.OFFICER_RECORDED. The GHC or GRM Unit
    officer digitises a walk-in, physical form, or other offline source.
    """
    # ── Two-way AI conversation channels ──────────────────────────────────────
    SMS             = "sms"             # Consumer sends SMS; LLM replies and collects details
    WHATSAPP        = "whatsapp"        # Consumer messages on WhatsApp; LLM replies
    WHATSAPP_VOICE  = "whatsapp_voice"  # Consumer sends a WhatsApp voice note; STT -> LLM pipeline
    PHONE_CALL      = "phone_call"      # Consumer calls; LLM/IVR guides them, or officer records

    # ── Self-service digital channels ─────────────────────────────────────────
    MOBILE_APP    = "mobile_app"    # Consumer uses the Riviwa mobile app (text or mic input)
    WEB_PORTAL    = "web_portal"    # Consumer uses the web frontend (text or mic input)

    # ── Officer-recorded / offline channels ───────────────────────────────────
    IN_PERSON     = "in_person"     # Consumer walked into a GRM Unit/LGA office
    PAPER_FORM    = "paper_form"    # Physical grievance registration form (Annex 5/6)
    EMAIL         = "email"         # Consumer emailed the GRM Unit/LGA
    PUBLIC_MEETING = "public_meeting" # Raised during a SEP consultation activity
    NOTICE_BOX    = "notice_box"    # Dropped in a suggestion/complaint box
    OTHER         = "other"

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        # Short-hand aliases clients may send
        aliases = {
            "web":        cls.WEB_PORTAL,
            "mobile":     cls.MOBILE_APP,
            "app":        cls.MOBILE_APP,
            "call":       cls.PHONE_CALL,
            "voice":      cls.PHONE_CALL,
            "walk_in":    cls.IN_PERSON,
            "walk-in":    cls.IN_PERSON,
            "meeting":    cls.PUBLIC_MEETING,
            "paper":      cls.PAPER_FORM,
            "form":       cls.PAPER_FORM,
            "wa":         cls.WHATSAPP,
            "wa_voice":   cls.WHATSAPP_VOICE,
            # Integration bridge channels
            "api":        cls.OTHER,
            "web_widget": cls.WEB_PORTAL,
            "mini_app":   cls.MOBILE_APP,
            "chatbot":    cls.OTHER,
            "partner_api": cls.OTHER,
        }
        if clean in aliases:
            return aliases[clean]
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class SubmissionMethod(str, Enum):
    """
    WHO created the Feedback record — distinct from the channel.

    SELF_SERVICE     → Consumer submitted directly (mobile_app, web_portal).
                       submitted_by_user_id or submitted_by_stakeholder_id is set.

    AI_CONVERSATION  → LLM collected details through a two-way conversation
                       (sms, whatsapp, phone_call). channel_session_id is set.
                       The LLM auto-submitted once it had sufficient information.

    OFFICER_RECORDED → A GHC officer or GRM Unit staff member entered the record on
                       behalf of the Consumer (walk-in, paper form, telephone call
                       manually transcribed). entered_by_user_id is set.
                       Used for in_person, paper_form, email, public_meeting,
                       notice_box, and officer-assisted sms/call/whatsapp.
    """
    SELF_SERVICE     = "self_service"
    AI_CONVERSATION  = "ai_conversation"
    OFFICER_RECORDED = "officer_recorded"


class SessionStatus(str, Enum):
    """Lifecycle of a two-way channel conversation session."""
    ACTIVE      = "active"      # Conversation in progress
    COMPLETED   = "completed"   # LLM submitted the Feedback record successfully
    ABANDONED   = "abandoned"   # Consumer stopped responding
    TIMED_OUT   = "timed_out"   # No activity for > SESSION_TIMEOUT_MINUTES
    FAILED      = "failed"      # Technical failure (gateway error, LLM error)


class FeedbackCategory(str, Enum):
    """
    What the feedback is about. Applies across all three FeedbackTypes —
    though not all categories are relevant to all types.

    GRIEVANCE categories (typical):
      COMPENSATION, RESETTLEMENT, LAND_ACQUISITION, CONSTRUCTION_IMPACT,
      TRAFFIC, WORKER_RIGHTS, SAFETY_HAZARD, ENVIRONMENTAL, ENGAGEMENT,
      DESIGN_ISSUE, PROJECT_DELAY, CORRUPTION, OTHER

    SUGGESTION categories (typical):
      DESIGN, PROCESS, COMMUNICATION, COMMUNITY_BENEFIT, EMPLOYMENT,
      SAFETY, ENVIRONMENTAL, ACCESSIBILITY, OTHER

    APPLAUSE categories (typical):
      QUALITY, TIMELINESS, STAFF_CONDUCT, COMMUNITY_IMPACT,
      RESPONSIVENESS, OTHER
    """
    # Shared
    COMMUNICATION    = "communication"
    SAFETY           = "safety"
    ENVIRONMENTAL    = "environmental"
    ACCESSIBILITY    = "accessibility"
    OTHER            = "other"

    # Primarily GRIEVANCE
    COMPENSATION     = "compensation"
    RESETTLEMENT     = "resettlement"
    LAND_ACQUISITION = "land_acquisition"
    CONSTRUCTION_IMPACT = "construction_impact"
    TRAFFIC          = "traffic"
    WORKER_RIGHTS    = "worker_rights"
    SAFETY_HAZARD    = "safety_hazard"
    ENGAGEMENT       = "engagement"
    DESIGN_ISSUE     = "design_issue"
    PROJECT_DELAY    = "project_delay"
    CORRUPTION       = "corruption"

    # Primarily SUGGESTION
    DESIGN           = "design"
    PROCESS          = "process"
    COMMUNITY_BENEFIT = "community_benefit"
    EMPLOYMENT       = "employment"

    # Primarily APPLAUSE
    QUALITY          = "quality"
    TIMELINESS       = "timeliness"
    STAFF_CONDUCT    = "staff_conduct"
    COMMUNITY_IMPACT = "community_impact"
    RESPONSIVENESS   = "responsiveness"

    # Primarily INQUIRY
    INFORMATION_REQUEST = "information_request"
    PROCEDURE_INQUIRY   = "procedure_inquiry"
    STATUS_UPDATE       = "status_update"
    DOCUMENT_REQUEST    = "document_request"
    GENERAL_INQUIRY     = "general_inquiry"

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class ActionType(str, Enum):
    """Type of action logged against a feedback item."""
    ACKNOWLEDGEMENT   = "acknowledgement"   # receipt confirmed to submitter
    INVESTIGATION     = "investigation"     # fact-finding underway
    SITE_VISIT        = "site_visit"        # physical inspection conducted
    STAKEHOLDER_MEETING = "stakeholder_meeting" # meeting held with submitter
    INTERNAL_REVIEW   = "internal_review"   # internal deliberation
    RESPONSE          = "response"          # formal response sent to submitter
    ESCALATION_NOTE   = "escalation_note"   # note added on escalation
    RESOLUTION_DRAFT  = "resolution_draft"  # resolution being drafted
    APPEAL_REVIEW     = "appeal_review"     # appeal being considered
    NOTE              = "note"              # general internal note


class ResponseMethod(str, Enum):
    """How the response was communicated to the submitter."""
    VERBAL            = "verbal"
    WRITTEN_LETTER    = "written_letter"
    EMAIL             = "email"
    SMS               = "sms"
    PHONE_CALL        = "phone_call"
    IN_PERSON_MEETING = "in_person_meeting"
    NOTICE_BOARD      = "notice_board"
    OTHER             = "other"


class CommitteeLevel(str, Enum):
    """What GRM level this committee operates at."""
    WARD              = "ward"
    LGA_GRM_UNIT      = "lga_grm_unit"
    COORDINATING_UNIT = "coordinating_unit"
    TARURA_WBCU       = "tarura_wbcu"
    TANROADS          = "tanroads"


class CommitteeRole(str, Enum):
    CHAIRPERSON = "chairperson"
    SECRETARY   = "secretary"
    MEMBER      = "member"



class Feedback(SQLModel, table=True):
    """
    The single submission record for grievances, suggestions, and applause.

    Every submission — regardless of type — receives:
      · A human-readable unique_ref (e.g. GRV-2025-0001, SGG-2025-0023)
      · The full GRM chain (current_level, escalation history via FeedbackEscalation)
      · A status lifecycle from SUBMITTED to CLOSED
      · Optional submitter identity at three levels (user → stakeholder → contact)
      · Media attachments (photos, audio, video evidence)
      · Location context (where the issue occurred or was observed)

    ANONYMITY GUARANTEE
    ───────────────────
    When is_anonymous=True ALL identity fields are null. This is enforced at:
      1. DB CHECK constraint ck_anonymous_no_identity (database-level hard block)
      2. API serializer _feedback_out() (never returns identity in responses)
      3. Every submission path (feedback.py, consumer.py, channels.py) before INSERT
    """
    __tablename__ = "feedbacks"
    __table_args__ = (
        # Database-level anonymity enforcement.
        # Prevents identity leakage even if application code has a bug.
        # If is_anonymous=TRUE then all identity-bearing columns must be NULL.
        __import__("sqlalchemy").CheckConstraint(
            "(NOT is_anonymous) OR ("
            "    submitted_by_user_id IS NULL AND "
            "    submitted_by_stakeholder_id IS NULL AND "
            "    submitted_by_contact_id IS NULL AND "
            "    channel_session_id IS NULL AND "
            "    entered_by_user_id IS NULL"
            ")",
            name="ck_anonymous_no_identity",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Human-readable reference ───────────────────────────────────────────────
    # Format: {TYPE_PREFIX}-{YEAR}-{SEQUENCE} e.g. GRV-2025-0001
    # Generated by the service layer on create, unique across all feedback.
    unique_ref: str = Field(
        max_length=20,
        unique=True,
        index=True,
        nullable=False,
        description="Human-readable reference: GRV-2025-0001 / SGG-2025-0001 / APP-2025-0001",
    )

    # ── Project context ────────────────────────────────────────────────────────
    project_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    # Which project stage was active when feedback was submitted (for reporting)
    stage_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("fb_project_stages.id", ondelete="SET NULL"), nullable=True, index=True),
        description="Active ProjectStageCache.id at time of submission.",
    )
    # Sub-project context — which work package this feedback relates to
    subproject_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgSubProject.id — soft link to a specific work package. "
            "Null for project/stage-level feedback. Used for suggestion performance "
            "analytics filtered by sub-project."
        ),
    )

    # Department this feedback is directed at or handled by
    department_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgDepartment.id — soft link to the department responsible "
            "for or targeted by this feedback (e.g. HR, Finance, Customer Care). "
            "No DB-level FK (cross-database reference). Null = not department-specific."
        ),
    )

    # Branch this feedback belongs to (denormalised from department.branch_id at submission)
    branch_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgBranch.id — denormalised from OrgDepartment.branch_id at "
            "submission time when department_id is provided. Enables branch-level analytics "
            "without a cross-DB join. No DB-level FK (cross-database reference)."
        ),
    )

    # Optional: which specific service location the feedback is about
    service_location_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgServiceLocation.id — which specific deployment "
            "site this feedback is about. Null for project-level feedback."
        ),
    )

    # Which org service this feedback is about (soft link to auth_service OrgService)
    service_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgService.id — soft link to the specific service "
            "(service_type=SERVICE or PROGRAM) this feedback relates to. "
            "No DB-level FK (cross-database reference). Null = not service-specific."
        ),
    )

    # Which product this feedback is about (soft link to auth_service OrgService where service_type=PRODUCT)
    product_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service OrgService.id (service_type=PRODUCT) — soft link to "
            "the specific product this feedback relates to. "
            "No DB-level FK (cross-database reference). Null = not product-specific."
        ),
    )

    # ── Classification ─────────────────────────────────────────────────────────
    feedback_type: FeedbackType = Field(
        sa_column=Column(SAEnum(FeedbackType, name="feedback_type"), nullable=False, index=True)
    )
    # Legacy: hardcoded enum category — kept for backward compatibility on existing rows.
    # New submissions should use category_def_id (dynamic category table).
    # Both may be set on the same row; category_def_id takes precedence for display.
    category: FeedbackCategory = Field(
        sa_column=Column(SAEnum(FeedbackCategory, name="feedback_category"), nullable=False, index=True)
    )
    # Dynamic category — FK to FeedbackCategoryDef (nullable for backward compat).
    # When set, this is the authoritative category for analytics and filtering.
    # Assigned either by the submitter (from active category list), GRM Unit staff,
    # or the ML layer post-submission.
    category_def_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("feedback_category_defs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description=(
            "FK to FeedbackCategoryDef. Takes precedence over the legacy "
            "'category' enum field for analytics and filtering. "
            "Set by submitter, GRM Unit staff, or ML classifier."
        ),
    )
    # ML classification metadata — set when ML assigns or suggests the category
    ml_category_confidence: Optional[float] = Field(
        default=None, nullable=True,
        description="ML confidence (0.0–1.0) for the category_def_id assignment.",
    )
    ml_category_assigned_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When ML assigned or suggested the category.",
    )
    status: FeedbackStatus = Field(
        default=FeedbackStatus.SUBMITTED,
        sa_column=Column(SAEnum(FeedbackStatus, name="feedback_status"), nullable=False, index=True),
    )
    priority: FeedbackPriority = Field(
        default=FeedbackPriority.MEDIUM,
        sa_column=Column(SAEnum(FeedbackPriority, name="feedback_priority"), nullable=False, index=True),
        description="Set by GRM Unit on acknowledgement. Drives response timeframe.",
    )

    # ── GRM context ────────────────────────────────────────────────────────────
    current_level: GRMLevel = Field(
        default=GRMLevel.WARD,
        sa_column=Column(SAEnum(GRMLevel, name="grm_level"), nullable=False, index=True),
        description=(
            "Legacy GRM level enum. Kept for backward compatibility with analytics "
            "and Spark jobs. Updated in sync with current_level_id when grm_level_ref "
            "is set on the dynamic level. New logic should prefer current_level_id."
        ),
    )
    # ── Dynamic escalation path references ────────────────────────────────────
    # These fields power the new per-org configurable hierarchy.
    # They exist alongside the legacy current_level / GRMLevel fields so that
    # all existing analytics queries and Spark streaming jobs remain valid.
    escalation_path_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "EscalationPath.id resolved at submission time. "
            "NULL for legacy rows created before dynamic escalation was introduced."
        ),
    )
    current_level_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("escalation_levels.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description=(
            "Current EscalationLevel.id in the dynamic path. "
            "Updated on each escalation alongside current_level (backward compat). "
            "NULL for legacy rows or when no dynamic path is configured."
        ),
    )
    assigned_committee_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("grm_committees.id", ondelete="SET NULL"), nullable=True, index=True),
        description="GrievanceCommittee currently handling this feedback.",
    )
    assigned_to_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id of the GRM Unit staff member assigned to this.",
    )

    # ── Submission channel ─────────────────────────────────────────────────────
    channel: FeedbackChannel = Field(
        sa_column=Column(SAEnum(FeedbackChannel, name="feedback_channel"), nullable=False, index=True)
    )
    # WHO submitted this record — distinct from the channel.
    submission_method: SubmissionMethod = Field(
        default=SubmissionMethod.SELF_SERVICE,
        sa_column=Column(
            SAEnum(SubmissionMethod, name="submission_method"), nullable=False, index=True
        ),
        description=(
            "self_service = Consumer submitted directly (mobile_app, web_portal). "
            "ai_conversation = LLM collected via two-way chat (sms, whatsapp, phone_call). "
            "officer_recorded = GHC officer entered on behalf of Consumer (walk-in, paper form). "
            "Enables filtering: 'All officer-recorded grievances this month'."
        ),
    )
    # Set when submission_method = AI_CONVERSATION — links to the full conversation transcript.
    channel_session_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("channel_sessions.id", ondelete="SET NULL"), nullable=True, index=True
        ),
        description="ChannelSession.id — only set for AI_CONVERSATION submissions.",
    )

    # ── Submitter identity (three paths — see module docstring) ────────────────
    is_anonymous: bool = Field(
        default=False, nullable=False, index=True,
        description=(
            "True for anonymous submissions. When True, all three ID fields below "
            "should be null and submitter_name/phone are optional. "
            "Anonymity is preserved at every GRM level."
        ),
    )
    # Path 1: platform user
    submitted_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id — set when submitter has a Riviwa account.",
    )
    # Path 2: stakeholder contact (no platform account)
    submitted_by_stakeholder_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="stakeholder_service Stakeholder.id — the entity on whose behalf this was filed.",
    )
    submitted_by_contact_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="stakeholder_service StakeholderContact.id — the specific person who filed.",
    )
    # Path 3 / fallback: basic identity for non-platform submitters
    submitter_name:  Optional[str] = Field(default=None, max_length=200, nullable=True)
    submitter_phone: Optional[str] = Field(default=None, max_length=20,  nullable=True)
    submitter_location_region:   Optional[str] = Field(
        default=None, max_length=150, nullable=True,
        description="Submitter's administrative region. Annex 6 Complainant Details: Address (region).",
    )
    submitter_location_district: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Submitter's district. Annex 6 Complainant Details: District.",
    )
    submitter_location_lga:  Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Submitter's LGA / Municipal.",
    )
    submitter_location_ward: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Submitter's ward.",
    )
    submitter_location_street: Optional[str] = Field(
        default=None, max_length=200, nullable=True,
        description="Submitter's street / plot number. Annex 6 Complainant Details: Address.",
    )

    # ── Cross-service origin links (soft links) ────────────────────────────────
    # Set when feedback originates from a stakeholder engagement or distribution
    stakeholder_engagement_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "stakeholder_service StakeholderEngagement.id — "
            "set when this feedback was raised during a consultation activity."
        ),
    )
    distribution_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description=(
            "stakeholder_service CommunicationDistribution.id — "
            "set when this feedback arose from post-distribution concerns."
        ),
    )

    # ── Content ────────────────────────────────────────────────────────────────
    subject:     str           = Field(max_length=500, nullable=False)
    description: str           = Field(sa_column=Column(Text, nullable=False))
    media_urls:  Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True),
        description='Attached evidence: {"urls": ["https://cdn.riviwa.com/evidence/..."]}',
    )

    # ── Voice note (source-of-truth audio for any channel) ────────────────────
    # When a Consumer speaks into the mic (app/web/call) or an officer records a
    # walk-in conversation, the original audio is stored here permanently.
    # The transcription becomes the description if text was not separately typed.
    # This audio is the legal source-of-truth — it cannot be deleted.
    voice_note_url: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "URL of the original audio recording for this feedback. "
            "Set when channel = phone_call, whatsapp_voice, mobile_app (mic), "
            "web_portal (mic), or in_person (officer records). "
            "Stored in object storage (MinIO/S3). Never deleted — legal source of truth."
        ),
    )
    voice_note_transcription: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Full STT (speech-to-text) transcript of voice_note_url. "
            "Used to populate description if Consumer did not type text. "
            "Preserved separately from description so edits are traceable."
        ),
    )
    voice_note_duration_seconds: Optional[int] = Field(
        default=None, nullable=True,
        description="Duration of the voice note in seconds.",
    )
    voice_note_language: Optional[str] = Field(
        default=None, max_length=10, nullable=True,
        description="IETF language tag of the voice note: 'sw' (Swahili) or 'en' (English). Detected by STT.",
    )
    voice_note_transcription_confidence: Optional[float] = Field(
        default=None, nullable=True,
        description="STT confidence score (0.0–1.0). Low values flag the record for human review.",
    )
    voice_note_transcription_service: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="STT service used: 'whisper' | 'google_stt' | 'azure_stt' | 'manual'.",
    )

    # ── Location of the issue (Tanzania admin hierarchy + GPS) ───────────────
    # Maps directly to Annex 6 "Location of Grievance" section.
    # Full hierarchy: Region → District → LGA → Ward → Mtaa → GPS
    issue_location_description: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
        description="Free-text description of where the issue was observed e.g. 'Near Jangwani Bridge north abutment'.",
    )
    issue_region:   Optional[str] = Field(
        default=None, max_length=150, nullable=True,
        description="Administrative region e.g. 'Dar es Salaam', 'Coast'. Annex 6: Region.",
    )
    issue_district: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="District e.g. 'Ilala', 'Kinondoni'. Annex 6: District / Municipal.",
    )
    issue_lga:  Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Local Government Authority. Annex 6: Municipal.",
    )
    issue_ward: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Ward name e.g. 'Jangwani'. Annex 6: Division / Ward.",
    )
    issue_mtaa: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Sub-ward / cell (Mtaa) e.g. 'Mtaa wa Gerezani'. Annex 6: Street / Cell Location.",
    )
    issue_gps_lat: Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees latitude of the issue location. Annex 6: GPS Coordinates.",
    )
    issue_gps_lng: Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees longitude of the issue location. Annex 6: GPS Coordinates.",
    )

    # ── Timeline ───────────────────────────────────────────────────────────────
    date_of_incident: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the issue occurred (may differ from submission date).",
    )
    submitted_at:    datetime           = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    resolved_at:     Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    closed_at:       Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    target_resolution_date: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
        description="GRM Unit-set target date for resolution. Drives SLA monitoring.",
    )
    implemented_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description=(
            "SUGGESTION only — datetime the suggestion was formally marked as ACTIONED "
            "(implemented). Distinct from resolved_at to allow precise time-to-implement "
            "analytics. Auto-set when status → ACTIONED if not already populated."
        ),
    )

    # ── Staff notes (internal, not visible to submitter) ──────────────────────
    internal_notes: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Internal GRM Unit notes — never shown to the submitter.",
    )

    # ── Entry metadata ─────────────────────────────────────────────────────────
    # For in-person / paper submissions entered by staff on behalf of submitter
    entered_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of GRM Unit staff who entered this on behalf of the submitter.",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"),
            onupdate=text("now()"), nullable=False,
        )
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    project:     ProjectCache                 = Relationship(back_populates="feedbacks")
    category_def: "FeedbackCategoryDef" = Relationship(
        back_populates="feedbacks",
        sa_relationship_kwargs={"foreign_keys": "[Feedback.category_def_id]"},
    )
    actions:     List["FeedbackAction"]     = Relationship(
        back_populates="feedback",
        sa_relationship_kwargs={"order_by": "FeedbackAction.performed_at"},
    )
    escalations: List["FeedbackEscalation"] = Relationship(
        back_populates="feedback",
        sa_relationship_kwargs={"order_by": "FeedbackEscalation.escalated_at"},
    )
    resolution:  Optional["FeedbackResolution"] = Relationship(back_populates="feedback")
    appeal:      Optional["FeedbackAppeal"]     = Relationship(back_populates="feedback")
    committee:   Optional["GrievanceCommittee"] = Relationship(
        back_populates="feedbacks",
        sa_relationship_kwargs={"foreign_keys": "[Feedback.assigned_committee_id]"},
    )
    escalation_requests: List["EscalationRequest"] = Relationship(
        back_populates="feedback",
        sa_relationship_kwargs={"order_by": "EscalationRequest.requested_at"},
    )

    # ── Domain helpers ─────────────────────────────────────────────────────────

    def is_open(self) -> bool:
        return self.status not in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED)

    def is_resolved(self) -> bool:
        return self.status in (FeedbackStatus.RESOLVED, FeedbackStatus.CLOSED)

    def can_escalate(self) -> bool:
        return self.status in (
            FeedbackStatus.SUBMITTED,
            FeedbackStatus.ACKNOWLEDGED,
            FeedbackStatus.IN_REVIEW,
        )

    def can_resolve(self) -> bool:
        return self.status in (
            FeedbackStatus.SUBMITTED,
            FeedbackStatus.ACKNOWLEDGED,
            FeedbackStatus.IN_REVIEW,
            FeedbackStatus.ESCALATED,
        )

    def can_appeal(self) -> bool:
        return self.status == FeedbackStatus.RESOLVED and self.appeal is None

    def next_grm_level(self) -> Optional[GRMLevel]:
        """Returns the next level in the GRM hierarchy, or None if at the top."""
        order = [
            GRMLevel.WARD,
            GRMLevel.LGA_GRM_UNIT,
            GRMLevel.COORDINATING_UNIT,
            GRMLevel.TARURA_WBCU,
            GRMLevel.TANROADS,
            GRMLevel.WORLD_BANK,
        ]
        try:
            idx = order.index(self.current_level)
            return order[idx + 1] if idx + 1 < len(order) else None
        except ValueError:
            return None

    def __repr__(self) -> str:
        return (
            f"<Feedback {self.unique_ref} "
            f"[{self.feedback_type}/{self.status}] "
            f"level={self.current_level}>"
        )



class FeedbackAction(SQLModel, table=True):
    """
    Immutable audit log entry for every action taken on a Feedback record.

    A FeedbackAction is created for every meaningful step:
      · GRM Unit acknowledges receipt → ACKNOWLEDGEMENT
      · Fact-finding begins → INVESTIGATION
      · Site visit conducted → SITE_VISIT
      · Meeting with submitter → STAKEHOLDER_MEETING
      · Formal response sent → RESPONSE
      · Feedback escalated → ESCALATION_NOTE (alongside FeedbackEscalation)
      · Internal deliberation → INTERNAL_REVIEW
      · Any note added → NOTE

    The `response_method` and `response_summary` are populated for RESPONSE
    actions — they document how and what was communicated back to the submitter.
    This is the evidence trail the SEP requires.
    """
    __tablename__ = "feedback_actions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    feedback_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("feedbacks.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    action_type: ActionType = Field(
        sa_column=Column(SAEnum(ActionType, name="action_type"), nullable=False, index=True)
    )
    description: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Narrative description of the action taken.",
    )

    # For RESPONSE actions — how was the submitter informed?
    response_method:  Optional[ResponseMethod] = Field(
        default=None,
        sa_column=Column(SAEnum(ResponseMethod, name="response_method"), nullable=True),
    )
    response_summary: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Summary of what was communicated to the submitter.",
    )

    # Visibility — INTERNAL notes never shown to submitter
    is_internal: bool = Field(
        default=False, nullable=False,
        description="True = internal GRM Unit note, not visible to the submitter.",
    )

    performed_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the staff member who took this action.",
    )
    performed_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    feedback: Feedback = Relationship(back_populates="actions")

    def __repr__(self) -> str:
        return f"<FeedbackAction [{self.action_type}] feedback={self.feedback_id}>"



class FeedbackEscalation(SQLModel, table=True):
    """
    Records each escalation event in the GRM hierarchy.

    When a feedback is escalated:
      1. Feedback.current_level is updated to to_level
      2. Feedback.status is set to ESCALATED
      3. A FeedbackEscalation row is created
      4. A FeedbackAction row is created (action_type=ESCALATION_NOTE)
      5. The receiving committee (if identified) is set on Feedback.assigned_committee_id

    The `reason` field is MANDATORY — the SEP requires documented justification
    for every escalation. "Not resolved at lower level" is not sufficient;
    the specific reason (nature of grievance, timelines missed, etc.) must be stated.

    `escalated_to_committee_id` is set when the receiving GHC is known at
    the time of escalation. It may be null for upper levels (PCU, TANROADS)
    where the committee is not tracked in this system.
    """
    __tablename__ = "feedback_escalations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    feedback_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("feedbacks.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    from_level: GRMLevel = Field(
        sa_column=Column(SAEnum(GRMLevel, name="grm_from_level"), nullable=False)
    )
    to_level: GRMLevel = Field(
        sa_column=Column(SAEnum(GRMLevel, name="grm_to_level"), nullable=False, index=True)
    )
    # Dynamic path references — set alongside from/to_level for new escalations
    from_level_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("escalation_levels.id", ondelete="SET NULL"), nullable=True
        ),
        description="EscalationLevel.id escalated FROM. NULL for legacy rows.",
    )
    to_level_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("escalation_levels.id", ondelete="SET NULL"), nullable=True, index=True
        ),
        description="EscalationLevel.id escalated TO. NULL for legacy rows.",
    )
    reason: str = Field(
        sa_column=Column(Text, nullable=False),
        description="MANDATORY: documented reason for escalation.",
    )
    escalated_to_committee_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("grm_committees.id", ondelete="SET NULL"), nullable=True),
        description="GrievanceCommittee at the receiving level, if known.",
    )
    escalated_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id who initiated the escalation.",
    )
    escalated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    feedback:                  Feedback                      = Relationship(back_populates="escalations")
    escalated_to_committee:    Optional["GrievanceCommittee"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[FeedbackEscalation.escalated_to_committee_id]"}
    )

    def __repr__(self) -> str:
        return (
            f"<FeedbackEscalation {self.from_level}→{self.to_level} "
            f"feedback={self.feedback_id}>"
        )



class FeedbackResolution(SQLModel, table=True):
    """
    Formal resolution record — maps directly to the SEP Resolution Form (Annex 6).

    One resolution per feedback. When status = RESOLVED:
      · This row must exist.
      · resolution_summary describes what was decided.
      · grievant_satisfied records whether the submitter accepted the resolution.
      · If grievant_satisfied = False → appeal_filed may become True.

    Fields map directly to SEP Annex 6:
      resolution_summary  → "Response of complaint"
      grievant_response   → "Acknowledgement of resolution of grievance"
      grievant_satisfied  → determines if appeal is filed
      witness_name        → "Name of witness (if available)"
      resolved_by_user_id → "Name of project personnel"
    """
    __tablename__ = "feedback_resolutions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    feedback_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("feedbacks.id", ondelete="CASCADE"),
            unique=True,    # 1-to-1 with Feedback
            nullable=False,
            index=True,
        )
    )

    resolution_summary: str = Field(
        sa_column=Column(Text, nullable=False),
        description="What was decided and communicated to the submitter.",
    )
    response_method: ResponseMethod = Field(
        default=ResponseMethod.IN_PERSON_MEETING,
        sa_column=Column(SAEnum(ResponseMethod, name="resolution_response_method"), nullable=False),
        description="How the resolution was communicated.",
    )

    # Submitter response to the resolution
    grievant_satisfied: Optional[bool] = Field(
        default=None, nullable=True,
        description=(
            "True = submitter accepted the resolution. "
            "False = submitter is not satisfied (appeal may follow). "
            "Null = submitter response not yet received."
        ),
    )
    grievant_response: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="What the submitter said in response to the resolution.",
    )

    # Appeal trigger
    appeal_filed: bool = Field(
        default=False, nullable=False,
        description="True when grievant formally appealed. Triggers FeedbackAppeal creation.",
    )

    # SEP Annex 6 fields
    witness_name: Optional[str] = Field(default=None, max_length=200, nullable=True)
    resolved_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the GRM Unit staff who delivered the resolution.",
    )
    resolved_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    feedback: Feedback = Relationship(back_populates="resolution")

    def __repr__(self) -> str:
        return (
            f"<FeedbackResolution feedback={self.feedback_id} "
            f"satisfied={self.grievant_satisfied} appeal={self.appeal_filed}>"
        )



class FeedbackAppeal(SQLModel, table=True):
    """
    Appeal against a resolution. One-to-one with Feedback (only one appeal per item).

    When an appeal is filed:
      1. Feedback.status → APPEALED
      2. FeedbackAppeal row created
      3. FeedbackEscalation row created (with reason = appeal grounds)
      4. Feedback auto-escalates to the next GRM level for appeal review

    The SEP explicitly states the GRM must include "an opportunity for seeking
    redress from the courts if the affected person is not satisfied with the
    decision" — `court_referral_date` captures if the submitter took it further.
    """
    __tablename__ = "feedback_appeals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    feedback_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("feedbacks.id", ondelete="CASCADE"),
            unique=True,    # 1-to-1
            nullable=False,
            index=True,
        )
    )

    appeal_grounds: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Why the submitter is appealing — what they found unsatisfactory.",
    )
    appeal_outcome: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Result of the appeal review.",
    )

    appeal_status: str = Field(
        default="pending",
        max_length=30,
        nullable=False,
        description="pending | under_review | upheld | dismissed | referred_to_court",
    )

    # SEP requirement: court referral pathway
    court_referral_date: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Date submitter notified of their right to/took court referral.",
    )

    filed_by_user_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    reviewed_by_user_id: Optional[uuid.UUID] = Field(default=None, nullable=True)

    filed_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    reviewed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    feedback: Feedback = Relationship(back_populates="appeal")

    def __repr__(self) -> str:
        return f"<FeedbackAppeal feedback={self.feedback_id} status={self.appeal_status}>"



class GrievanceCommittee(SQLModel, table=True):
    """
    A Grievance Handling Committee (GHC) instance.

    The SEP mandates GHCs at:
      · Each Ward / sub-project area     (WARD)
      · Each LGA GRM Unit level                (LGA_PIU)
      · Coordinating Unit (PO-RALG/TARURA WBCU)  (PCU)
      · TANROADs                         (TANROADS)

    SCOPE LINKAGE
    ─────────────
    A committee is scoped by three optional axes:
      project_id          → the project it serves (null = all projects in this LGA)
      lga                 → the Local Government Authority (geographic scope)
      org_sub_project_id  → soft link to auth_service OrgSubProject.id when the
                            committee is dedicated to a specific work package.
                            NOT a FK constraint (cross-service). Allows querying:
                            "which committee handles sub-project SP-001?"

    STAKEHOLDER COVERAGE
    ─────────────────────
    stakeholder_ids (JSONB) lists the stakeholder_service Stakeholder UUIDs that
    this committee is responsible for. A ward GHC might cover:
      ["<M18 community UUID>", "<Jangwani residents UUID>"]
    This is a soft list — no FK constraints across service boundaries.
    Used for the query: "which committee handles grievances from stakeholder X?"
    and for reporting: "all grievances from stakeholder group Y at this level."

    Feedbacks are assigned to a committee via Feedback.assigned_committee_id.
    """
    __tablename__ = "grm_committees"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    name:  str = Field(max_length=255, nullable=False, index=True)
    level: CommitteeLevel = Field(
        sa_column=Column(SAEnum(CommitteeLevel, name="committee_level"), nullable=False, index=True)
    )

    # ── Project + geographic scope ─────────────────────────────────────────────
    # null project_id = committee handles all projects in this LGA
    project_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    )
    lga:        Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)

    # ── Sub-project scope — soft link to auth_service OrgSubProject ────────────
    # Set when this committee is dedicated to a specific sub-project / work package.
    # NOT a FK constraint — cross-service soft link.
    # Query: "which committee handles sub-project <UUID>?" →
    #   SELECT * FROM grm_committees WHERE org_sub_project_id = :sp_id
    org_sub_project_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "auth_service OrgSubProject.id — set when this committee is scoped to "
            "a specific work package. NOT a FK constraint."
        ),
    )

    # ── Stakeholder coverage — which stakeholder groups this committee covers ──
    # JSONB array of stakeholder_service Stakeholder UUIDs.
    # Format: {"stakeholder_ids": ["<uuid1>", "<uuid2>"]}
    # Enables queries:
    #   "Which committee handles the M18 flood community's grievances at ward level?"
    #   "All grievances from Jangwani residents group at LGA GRM Unit level"
    # NOT FK constraints — soft links maintained by GRM Unit staff at setup time.
    stakeholder_ids: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            "JSONB array of stakeholder_service Stakeholder UUIDs this committee "
            "covers. Format: {\"stakeholder_ids\": [\"<uuid>\", ...]}. "
            "Soft links — no FK constraints across service boundaries."
        ),
    )

    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    is_active: bool = Field(default=True, nullable=False, index=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False)
    )

    members:   List["GrievanceCommitteeMember"] = Relationship(
        back_populates="committee",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    feedbacks: List[Feedback] = Relationship(back_populates="committee")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def covers_stakeholder(self, stakeholder_id: str) -> bool:
        """True if this committee is scoped to include this stakeholder."""
        if not self.stakeholder_ids:
            return False
        return stakeholder_id in (self.stakeholder_ids.get("stakeholder_ids") or [])

    def get_stakeholder_ids(self) -> list[str]:
        """Return the list of covered stakeholder UUIDs (empty list if none set)."""
        if not self.stakeholder_ids:
            return []
        return self.stakeholder_ids.get("stakeholder_ids") or []

    def __repr__(self) -> str:
        return f"<GrievanceCommittee {self.name!r} [{self.level}]>"



class GrievanceCommitteeMember(SQLModel, table=True):
    """
    Junction: auth_service User ↔ GrievanceCommittee, with their role.

    UNIQUE (committee_id, user_id) — one membership per person per committee.
    A person can sit on multiple committees (e.g. Ward GHC and LGA GRM Unit GHC).
    """
    __tablename__ = "grm_committee_members"
    __table_args__ = (UniqueConstraint("committee_id", "user_id", name="uq_committee_member"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    committee_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("grm_committees.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    # auth_service User.id — NOT a FK constraint (cross-service)
    user_id: uuid.UUID = Field(nullable=False, index=True)

    role: CommitteeRole = Field(
        sa_column=Column(SAEnum(CommitteeRole, name="committee_role"), nullable=False)
    )

    is_active: bool = Field(default=True, nullable=False)
    joined_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    left_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    committee: GrievanceCommittee = Relationship(back_populates="members")

    def __repr__(self) -> str:
        return (
            f"<GrievanceCommitteeMember user={self.user_id} "
            f"committee={self.committee_id} role={self.role}>"
        )



class CategorySource(str, Enum):
    """
    How this category was created.

    SYSTEM  → pre-seeded at startup from the FeedbackCategory enum.
               These are the platform defaults that always exist.
               Cannot be deleted; can be deactivated per project.

    MANUAL  → created explicitly by a GRM Unit staff member or GHC member
               via POST /api/v1/categories. Full CRUD available.

    ML      → auto-created by the AI classification layer after reading
               the context of a feedback submission that didn't match
               any existing active category. The ML suggests the new
               category name; a human must approve it before it becomes
               visible for filtering (status = pending_review).
               Once approved (status = active) it behaves like MANUAL.
    """
    SYSTEM = "system"
    MANUAL = "manual"
    ML     = "ml"


class CategoryStatus(str, Enum):
    """
    Lifecycle of a category definition.

    ACTIVE          → visible, can be assigned to feedback submissions.
    PENDING_REVIEW  → ML-suggested; awaiting human approval.
                      Not shown to submitters. Cannot be filtered on.
                      GRM Unit staff can approve → ACTIVE or reject → REJECTED.
    INACTIVE        → deactivated by GRM Unit (too granular, merged elsewhere).
                      Existing feedback with this category is unaffected.
                      Cannot be assigned to new submissions.
    REJECTED        → ML suggestion was wrong; permanently dismissed.
    """
    ACTIVE         = "active"
    PENDING_REVIEW = "pending_review"
    INACTIVE       = "inactive"
    REJECTED       = "rejected"


class FeedbackCategoryDef(SQLModel, table=True):
    """
    Dynamic category definitions for feedback submissions.

    Replaces the hardcoded FeedbackCategory enum for new submissions while
    remaining backward-compatible (the enum is preserved for existing rows
    and as a seed source).

    DESIGN GOALS
    ─────────────
    1. GHC members and GRM Unit staff can create project-specific categories
       that make sense for their particular context. "Msimbazi Flood Risk"
       is meaningful for that project but would not be in a global enum.

    2. ML reads the full text of each feedback submission and assigns the
       best matching category from active categories. If no match exceeds
       the confidence threshold, ML auto-creates a new PENDING_REVIEW
       category and flags it for human review. Human reviews it in the
       admin panel and either approves or rejects it.

    3. Once categories exist, the analytics layer (GET /api/v1/categories/{id}/rate)
       can answer "how many grievances about compensation per week?" in real
       time or over any date range — enabling GRM Unit to spot emerging patterns
       before they escalate.

    SCOPE
    ──────
    project_id = NULL  → platform-wide category (e.g. "compensation", "safety")
    project_id set     → project-specific category (e.g. "Msimbazi flood relocation")

    When a submission comes in for project X, the category picker shows:
      1. Active platform-wide categories (project_id=NULL)
      2. Active project-specific categories for project X
      3. "other" as a fallback

    ML CONFIDENCE
    ──────────────
    ml_confidence (0.0 – 1.0) is only set when source=ML.
    Values:
      ≥ 0.85 → ML is confident; auto-assigns and sets status=ACTIVE
      0.60–0.84 → ML is uncertain; creates PENDING_REVIEW, flags for human
      < 0.60 → ML cannot classify; assigns "other" and logs for review

    MERGE SUPPORT
    ──────────────
    merged_into_id lets GRM Unit staff consolidate overlapping categories.
    All existing feedback tagged with this category keeps its assignment
    (for historical reporting); new submissions cannot use a merged category.

    Relationship wiring:
      FeedbackCategoryDef.project    ←→  ProjectCache.categories (back-pop)
      FeedbackCategoryDef.feedbacks  ←→  Feedback.category_def
    """
    __tablename__ = "feedback_category_defs"
    __table_args__ = (
        UniqueConstraint("slug", "project_id", name="uq_category_slug_per_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = Field(
        max_length=150, nullable=False, index=True,
        description="Human-readable name e.g. 'Compensation for land loss', 'Construction noise'.",
    )
    slug: str = Field(
        max_length=100, nullable=False, index=True,
        description="URL-safe identifier e.g. 'compensation-land-loss'. Unique per project.",
    )
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="What this category covers — used by ML as part of classification context.",
    )

    # ── Scope ─────────────────────────────────────────────────────────────────
    project_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="SET NULL"), nullable=True, index=True),
        description="Null = platform-wide. Set = project-specific category.",
    )

    # ── Applicable feedback types ──────────────────────────────────────────────
    # JSONB array: ["grievance", "suggestion", "applause"] or subset
    applicable_types: Dict[str, Any] = Field(
        default={"types": ["grievance", "suggestion", "applause", "inquiry"]},
        sa_column=Column(JSONB, nullable=False),
        description=(
            "Which feedback types this category applies to. "
            'Format: {"types": ["grievance", "suggestion"]}. '
            "Drives the category picker shown to submitters."
        ),
    )

    # ── Provenance ────────────────────────────────────────────────────────────
    source: CategorySource = Field(
        default=CategorySource.MANUAL,
        sa_column=Column(SAEnum(CategorySource, name="category_source"), nullable=False, index=True),
    )
    status: CategoryStatus = Field(
        default=CategoryStatus.ACTIVE,
        sa_column=Column(SAEnum(CategoryStatus, name="category_status"), nullable=False, index=True),
    )

    # ── ML metadata (set only when source=ML) ─────────────────────────────────
    ml_confidence: Optional[float] = Field(
        default=None, nullable=True,
        description="ML classification confidence (0.0–1.0). Only set when source=ML.",
    )
    ml_model_version: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="Version of the ML model that created this category.",
    )
    ml_rationale: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="ML explanation of why it created this category.",
    )
    # The sample feedback submission that triggered this ML category creation
    triggered_by_feedback_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("feedbacks.id", ondelete="SET NULL"), nullable=True),
        description="Feedback submission that caused ML to create this category.",
    )

    # ── Human review ──────────────────────────────────────────────────────────
    reviewed_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id who approved or rejected this ML category.",
    )
    reviewed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    review_notes: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Why it was approved / rejected / deactivated.",
    )

    # ── Merge support ──────────────────────────────────────────────────────────
    merged_into_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("feedback_category_defs.id", ondelete="SET NULL"), nullable=True),
        description=(
            "Set when this category is consolidated into another. "
            "Historical feedback keeps this tag; new submissions must use merged_into_id category."
        ),
    )

    # ── Display ───────────────────────────────────────────────────────────────
    color_hex: Optional[str] = Field(
        default=None, max_length=7, nullable=True,
        description="Hex color for UI display e.g. '#E24B4A'. Set by GRM Unit staff.",
    )
    icon:      Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="Icon identifier for UI display.",
    )
    display_order: int = Field(
        default=0, nullable=False,
        description="Order in category picker (lower = earlier).",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id who created this category. Null for SYSTEM.",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    feedbacks: List[Feedback] = Relationship(
        back_populates="category_def",
        sa_relationship_kwargs={"foreign_keys": "[Feedback.category_def_id]"},
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_assignable(self) -> bool:
        """True when this category can be assigned to new submissions."""
        return self.status == CategoryStatus.ACTIVE and self.merged_into_id is None

    def applies_to(self, feedback_type: str) -> bool:
        """True when this category is valid for the given feedback_type."""
        types = (self.applicable_types or {}).get("types", [])
        return feedback_type in types

    def __repr__(self) -> str:
        return f"<FeedbackCategoryDef {self.slug!r} [{self.source}/{self.status}]>"



class ChannelSession(SQLModel, table=True):
    """
    A two-way conversation session between a Consumer and the LLM on a digital channel.

    Applies to channels: SMS, WHATSAPP, PHONE_CALL.

    LIFECYCLE
    ──────────
      1. Inbound message arrives at webhook (POST /webhooks/sms or /webhooks/whatsapp).
      2. System looks up existing ACTIVE session for this phone_number + project.
         If none found, creates a new ChannelSession (status=ACTIVE).
      3. User message is appended to turns[]. LLM is called with full history.
      4. LLM response is appended to turns[] and sent back via gateway.
      5. When LLM determines it has enough information, it calls the internal
         submit action → Feedback record is created → status=COMPLETED,
         feedback_id is set.
      6. If no activity for SESSION_TIMEOUT_MINUTES → status=TIMED_OUT.

    CONVERSATION TURNS
    ───────────────────
    turns (JSONB) stores the full conversation history:
      [
        {"role": "assistant", "content": "Habari! ...", "timestamp": "..."},
        {"role": "user",      "content": "Nina malalamiko...", "timestamp": "..."},
        ...
      ]

    EXTRACTED DATA
    ───────────────
    extracted_data (JSONB) is updated by the LLM after each turn as it
    progressively fills in the grievance fields from the conversation:
      {
        "feedback_type": "grievance",
        "subject": "...",
        "description": "...",
        "category_slug": "compensation",
        "lga": "Ilala",
        "incident_date": "2025-03-20",
        "confidence": 0.85,
        "fields_missing": ["full_name"]
      }
    When confidence ≥ 0.80 and no required fields are missing, the LLM submits.

    CHANNEL METADATA
    ─────────────────
    phone_number / whatsapp_id / caller_id: the identifier from the gateway
      (E.164 format for SMS/WhatsApp; caller ID for calls)
    gateway_session_id: the external session ID from the SMS/WhatsApp gateway
      (Twilio CallSid, Africa's Talking sessionId, etc.) for reconciliation
    language: detected or selected language code (sw=Swahili, en=English)

    OFFICER-ASSISTED
    ─────────────────
    is_officer_assisted=True: a GHC officer opened this session on behalf of a
      walk-in Consumer. recorded_by_user_id is set. The LLM still guides the
      structured collection but the officer types the Consumer's words.
    """
    __tablename__ = "channel_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Channel identity ──────────────────────────────────────────────────────
    channel: FeedbackChannel = Field(
        sa_column=Column(SAEnum(FeedbackChannel, name="channel_session_channel",
                                create_constraint=False), nullable=False, index=True),
        description="sms | whatsapp | phone_call only.",
    )
    project_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="SET NULL"), nullable=True, index=True),
        description="Resolved during conversation if not provided at session start.",
    )

    # ── Contact identification ────────────────────────────────────────────────
    # At least one of these is set based on the channel.
    phone_number: Optional[str] = Field(
        default=None, max_length=20, nullable=True, index=True,
        description="E.164 phone number for SMS and phone_call channels.",
    )
    whatsapp_id: Optional[str] = Field(
        default=None, max_length=50, nullable=True, index=True,
        description="WhatsApp sender ID (usually the E.164 phone number).",
    )
    # auth_service User.id — set after channel-register call succeeds.
    # This links the conversation to a real User account so that
    # feedback submitted via this session has submitted_by_user_id populated.
    user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description=(
            "auth_service User.id — populated on first message by calling "
            "POST /auth/channel-register. Links feedback to a real user account."
        ),
    )
    # Optional link to a known stakeholder contact if the number is recognised
    stakeholder_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="stakeholder_service Stakeholder.id — set if phone number matches a known contact.",
    )
    contact_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="stakeholder_service StakeholderContact.id — if number matches a contact.",
    )

    # ── Gateway metadata ──────────────────────────────────────────────────────
    gateway_session_id: Optional[str] = Field(
        default=None, max_length=255, nullable=True, index=True,
        description="External session ID from the SMS/WhatsApp gateway for reconciliation.",
    )
    gateway_provider: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="Gateway provider: twilio | africas_talking | nexmo | meta | other",
    )

    # ── Conversation state ────────────────────────────────────────────────────
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        sa_column=Column(SAEnum(SessionStatus, name="session_status"), nullable=False, index=True),
    )
    language: str = Field(
        default="sw", max_length=5, nullable=False,
        description="IETF language tag: 'sw' (Swahili) or 'en' (English). Detected on first turn.",
    )
    turns: Dict[str, Any] = Field(
        default={"turns": []},
        sa_column=Column(JSONB, nullable=False),
        description='JSONB array of conversation turns: {"turns": [{"role":...,"content":...,"ts":...}]}',
    )
    extracted_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Fields the LLM has extracted so far from the conversation.",
    )
    turn_count: int = Field(default=0, nullable=False)

    # ── Outcome ───────────────────────────────────────────────────────────────
    # Set when status=COMPLETED and the LLM successfully submitted a Feedback record.
    feedback_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("feedbacks.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    # Reason if status=ABANDONED/FAILED
    end_reason: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
    )

    # ── Officer-assisted mode ─────────────────────────────────────────────────
    is_officer_assisted: bool = Field(
        default=False, nullable=False,
        description="True when a GHC officer opened this session on behalf of a walk-in Consumer.",
    )
    recorded_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the officer who opened this session.",
    )

    # ── Voice / audio ─────────────────────────────────────────────────────────
    # Populated when is_voice_session=True.
    # For PHONE_CALL and IN_PERSON: one recording covers the full session.
    # For MOBILE_APP/WEB_PORTAL: each audio turn stored in turns[] JSONB plus
    # the concatenated full recording stored here on session completion.
    is_voice_session: bool = Field(
        default=False, nullable=False,
        description=(
            "True when the session used audio input (phone call, mic in app/web, "
            "WhatsApp voice note, or officer-recorded in-person conversation)."
        ),
    )
    audio_recording_url: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Full session audio recording URL. For PHONE_CALL/IN_PERSON: single "
            "recording of the entire conversation. For MOBILE_APP/WEB_PORTAL: "
            "concatenated audio of all voice turns. Never deleted — legal source of truth."
        ),
    )
    audio_duration_seconds: Optional[int] = Field(
        default=None, nullable=True,
        description="Total duration of audio_recording_url in seconds.",
    )
    transcription: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Full STT transcript of the entire session audio. "
            "Assembled from per-turn transcriptions stored in turns[] JSONB. "
            "This is the legal text record of the conversation."
        ),
    )
    transcription_service: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="STT service used: 'whisper' | 'google_stt' | 'azure_stt' | 'manual'.",
    )
    transcription_confidence: Optional[float] = Field(
        default=None, nullable=True,
        description="Average STT confidence score (0.0–1.0) across all voice turns.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    last_activity_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_turns(self) -> list[dict]:
        return (self.turns or {}).get("turns", [])

    def add_turn(
        self,
        role: str,
        content: str,
        audio_url: Optional[str] = None,
        is_voice: bool = False,
        transcription_confidence: Optional[float] = None,
    ) -> None:
        """
        Append a conversation turn in-place. Call db.add(session) after.

        For voice turns:
          - content       = STT transcript (used by LLM as the message text)
          - audio_url     = URL of this turn's audio file in object storage
          - is_voice      = True so the frontend knows to render an audio player
          - transcription_confidence = STT confidence for this specific turn

        Turn JSONB structure:
          {
            "role":    "user" | "assistant",
            "content": "Nina malalamiko kuhusu fidia...",
            "ts":      "2025-03-27T12:00:00+00:00",
            "audio_url": "https://cdn.riviwa.com/audio/session-uuid/turn-3.webm",
            "is_voice": true,
            "transcription_confidence": 0.91
          }
        """
        existing = self.get_turns()
        turn: dict = {
            "role":    role,
            "content": content,
            "ts":      datetime.now(timezone.utc).isoformat(),
        }
        if is_voice:
            turn["is_voice"] = True
        if audio_url:
            turn["audio_url"] = audio_url
        if transcription_confidence is not None:
            turn["transcription_confidence"] = transcription_confidence
        existing.append(turn)
        self.turns = {"turns": existing}
        self.turn_count = len(existing)
        self.last_activity_at = datetime.now(timezone.utc)

    def is_two_way_channel(self) -> bool:
        return self.channel in (
            FeedbackChannel.SMS,
            FeedbackChannel.WHATSAPP,
            FeedbackChannel.WHATSAPP_VOICE,
            FeedbackChannel.PHONE_CALL,
        )

    def is_voice_channel(self) -> bool:
        """True for channels that natively carry audio."""
        return self.channel in (
            FeedbackChannel.PHONE_CALL,
            FeedbackChannel.WHATSAPP_VOICE,
            FeedbackChannel.MOBILE_APP,
            FeedbackChannel.WEB_PORTAL,
            FeedbackChannel.IN_PERSON,
        )

    def __repr__(self) -> str:
        return (
            f"<ChannelSession {self.channel.value} "
            f"phone={self.phone_number or self.whatsapp_id!r} "
            f"[{self.status.value}] turns={self.turn_count}>"
        )



class EscalationRequestStatus(str, Enum):
    """Lifecycle of a Consumer escalation request."""
    PENDING   = "pending"    # Consumer submitted, GRM Unit has not yet reviewed
    APPROVED  = "approved"   # GRM Unit approved — escalation will proceed
    REJECTED  = "rejected"   # GRM Unit rejected — explained in reviewer_notes
    ACTIONED  = "actioned"   # GRM Unit escalated the grievance following approval

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        clean = value.strip().lower()
        for member in cls:
            if clean == member.value or clean == member.name.lower():
                return member
        return None


class EscalationRequest(SQLModel, table=True):
    """
    A formal request by the Consumer to escalate
    their grievance to the next GRM level.

    IMPORTANT DISTINCTION from FeedbackEscalation:
      FeedbackEscalation → staff-initiated, immediate, recorded in the GRM trail.
      EscalationRequest  → Consumer-initiated, goes to GRM Unit inbox for review.
                           GRM Unit can approve (→ triggers actual escalation) or
                           reject (→ must explain why in reviewer_notes).

    This exists because:
      1. The Consumer may feel their case is not progressing fast enough.
      2. The SEP requires Consumers to have a formal recourse channel.
      3. It creates an audit trail separate from the escalation trail,
         showing that the Consumer exercised their right to challenge the process.

    When status → APPROVED:
      GRM Unit calls POST /api/v1/feedback/{id}/escalate (staff endpoint)
      which creates the FeedbackEscalation and updates Feedback.current_level.
      Then sets EscalationRequest.status → ACTIONED.

    Relationship wiring:
      EscalationRequest.feedback ←→ Feedback.escalation_requests
    """
    __tablename__ = "escalation_requests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    feedback_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("feedbacks.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    # Consumer identity
    requested_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id of the Consumer who submitted this request.",
    )
    requested_by_stakeholder_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="stakeholder_service Stakeholder.id — if Consumer is a known stakeholder.",
    )

    # Request details
    reason: str = Field(
        sa_column=Column(Text, nullable=False),
        description=(
            "Why the Consumer wants escalation. Required. "
            "e.g. 'No response received for 14 days despite follow-up', "
            "'Resolution offered is insufficient compensation'."
        ),
    )
    requested_level: Optional[str] = Field(
        default=None, max_length=30, nullable=True,
        description="GRM level the Consumer wants to escalate to (optional — GRM Unit may override).",
    )

    status: EscalationRequestStatus = Field(
        default=EscalationRequestStatus.PENDING,
        sa_column=Column(
            SAEnum(EscalationRequestStatus, name="escalation_request_status"),
            nullable=False, index=True,
        ),
    )

    # GRM Unit review
    reviewed_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="GRM Unit staff who reviewed this request.",
    )
    reviewed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    reviewer_notes: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="GRM Unit explanation for approval or rejection (shown to Consumer if rejected).",
    )

    # Timestamps
    requested_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    feedback: Feedback = Relationship(back_populates="escalation_requests")

    def __repr__(self) -> str:
        return (
            f"<EscalationRequest feedback={self.feedback_id} "
            f"status={self.status.value}>"
        )
