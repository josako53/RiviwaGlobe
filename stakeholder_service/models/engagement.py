# ───────────────────────────────────────────────────────────────────────────
# SERVICE   :  stakeholder_service
# PORT      :  Port: 8070
# DATABASE  :  DB: stakeholder_db (5436)
# FILE      :  models/engagement.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/engagement.py
═══════════════════════════════════════════════════════════════════════════════
Two tables tracking consultation events and attendance.

  EngagementActivity     → a single consultation event (meeting, workshop, site visit)
  StakeholderEngagement  → who attended, what they said, what response was given

ENGAGEMENT STAGES (from the SEP)
──────────────────────────────────────────────────────────────────────────────
  PREPARATION         → before project approval; stakeholder identification
  FEASIBILITY_DESIGN  → technical design stage; design input consultations
  CONSTRUCTION        → during works; ESMP sensitisation, progress updates
  FINALIZATION        → project handover; feedback on outcomes
  OPERATION           → post-completion; ongoing monitoring

ACTIVITY TYPES (from the SEP engagement strategies)
──────────────────────────────────────────────────────────────────────────────
  PUBLIC_MEETING      → open community meeting (largest group)
  WORKSHOP            → structured working session (national/district level)
  FOCUS_GROUP         → small group by age, gender, occupation
  SITE_VISIT          → physical inspection of project area
  SURVEY              → written/digital questionnaire
  RADIO_TV            → broadcast engagement (awareness, call-in)
  SOCIAL_MEDIA        → online engagement (WhatsApp, Facebook, etc.)
  KEY_INFORMANT       → one-on-one interview with a stakeholder leader
  ROUND_TABLE         → multi-stakeholder discussion
  ONLINE_WEBINAR      → virtual meeting (Zoom, WebEx, Skype — COVID protocol)

RELATIONSHIP WIRING
──────────────────────────────────────────────────────────────────────────────
  EngagementActivity.project       ←→  Project.activities
  EngagementActivity.attendances   ←→  StakeholderEngagement.activity
  StakeholderEngagement.contact    ←→  StakeholderContact.engagements
═══════════════════════════════════════════════════════════════════════════════
"""
# NOTE: do NOT add `from __future__ import annotations` here.
# It stringifies all annotations at import time, which breaks SQLModel's
# List["Model"] relationship resolution.
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

# Runtime imports — SQLAlchemy mapper needs to resolve Relationship strings.
from models.project import ProjectCache, ProjectStageCache    # noqa: F401



class EngagementStage(str, Enum):
    PREPARATION        = "preparation"
    FEASIBILITY_DESIGN = "feasibility_design"
    CONSTRUCTION       = "construction"
    FINALIZATION       = "finalization"
    OPERATION          = "operation"


class ActivityType(str, Enum):
    PUBLIC_MEETING  = "public_meeting"
    WORKSHOP        = "workshop"
    FOCUS_GROUP     = "focus_group"
    SITE_VISIT      = "site_visit"
    SURVEY          = "survey"
    RADIO_TV        = "radio_tv"
    SOCIAL_MEDIA    = "social_media"
    KEY_INFORMANT   = "key_informant"
    ROUND_TABLE     = "round_table"
    ONLINE_WEBINAR  = "online_webinar"
    OTHER           = "other"


class ActivityStatus(str, Enum):
    PLANNED   = "planned"    # scheduled but not yet conducted
    CONDUCTED = "conducted"  # took place; attendance can be logged
    CANCELLED = "cancelled"  # did not happen; reason captured in notes


class AttendanceStatus(str, Enum):
    """
    Outcome of a contact's participation in an activity.

    ATTENDED:       Contact was present and participated.
    ABSENT:         Contact was invited but did not attend.
    REPRESENTED:    Contact sent a proxy/delegate.
    REMOTE:         Contact joined remotely (phone / webinar).
    """
    ATTENDED    = "attended"
    ABSENT      = "absent"
    REPRESENTED = "represented"
    REMOTE      = "remote"



class EngagementActivity(SQLModel, table=True):
    """
    A single consultation or engagement event for a project.

    Each activity is tied to a project and a stage in the project lifecycle.
    The actual participants are tracked via StakeholderEngagement rows.

    Key fields:
      · lga / ward:          where the activity takes place (for reports)
      · conducted_by_user_id: auth_service User who ran the session
      · minutes_url:          link to the written minutes (CDN / S3)
      · expected_count:       planned attendance for monitoring/reporting
      · actual_count:         recorded actual attendance
      · summary_of_issues:    high-level summary of concerns raised
                              (detail lives on StakeholderEngagement rows)
    """
    __tablename__ = "engagement_activities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    project_id: uuid.UUID = Field(nullable=False, index=True,
                                   description="ProjectCache (OrgProject) this activity is for.")

    # ── Stage and sub-project context ─────────────────────────────────────────
    stage_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "ProjectStageCache.id — which stage of the project this activity belongs to. "
            "Null for project-level activities not tied to a specific stage."
        ),
    )
    subproject_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "auth_service OrgSubProject.id — if this engagement is specifically "
            "about a sub-project (e.g. a consultation on the River Dredging sub-project). "
            "Soft link — no FK constraint. Null for stage-level activities."
        ),
    )

    # ── Classification ────────────────────────────────────────────────────────
    stage: EngagementStage = Field(
        sa_column=Column(SAEnum(EngagementStage, name="engagement_stage"), nullable=False, index=True)
    )
    activity_type: ActivityType = Field(
        sa_column=Column(SAEnum(ActivityType, name="activity_type"), nullable=False, index=True)
    )
    status: ActivityStatus = Field(
        default=ActivityStatus.PLANNED,
        sa_column=Column(SAEnum(ActivityStatus, name="activity_status"), nullable=False, index=True),
    )

    # ── Event details ─────────────────────────────────────────────────────────
    title:       str           = Field(max_length=255, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    agenda:      Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Structured agenda for the session.",
    )

    # ── Location ──────────────────────────────────────────────────────────────
    # Physical location fields
    venue:        Optional[str] = Field(default=None, max_length=500, nullable=True,
                                         description="Venue name and address for physical meetings.")
    lga:          Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    ward:         Optional[str] = Field(default=None, max_length=100, nullable=True)
    gps_lat:      Optional[float] = Field(default=None, nullable=True)
    gps_lng:      Optional[float] = Field(default=None, nullable=True)

    # Virtual location fields (for online_webinar / COVID-19 protocol)
    virtual_platform: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="e.g. 'Zoom', 'WebEx', 'Skype', 'WhatsApp'",
    )
    virtual_url: Optional[str] = Field(default=None, max_length=1024, nullable=True)
    virtual_meeting_id: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Meeting ID / dial-in number for virtual sessions.",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────
    scheduled_at:  Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    conducted_at:  Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Actual date/time the activity took place. Set when status → CONDUCTED.",
    )
    duration_hours: Optional[float] = Field(
        default=None, nullable=True,
        description="Duration of the session in hours.",
    )

    # ── Languages ─────────────────────────────────────────────────────────────
    languages_used: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='JSONB array of language codes e.g. {"languages": ["sw", "en", "sign"]}',
    )

    # ── Attendance tracking ───────────────────────────────────────────────────
    expected_count: Optional[int] = Field(
        default=None, nullable=True,
        description="Planned number of attendees (for monitoring / reporting).",
    )
    actual_count: Optional[int] = Field(
        default=None, nullable=True,
        description="Actual attendance count recorded after the session.",
    )
    female_count: Optional[int] = Field(
        default=None, nullable=True,
        description="Number of female attendees (gender disaggregated reporting).",
    )
    vulnerable_count: Optional[int] = Field(
        default=None, nullable=True,
        description="Number of attendees from vulnerable groups.",
    )

    # ── Outcomes ──────────────────────────────────────────────────────────────
    summary_of_issues: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "High-level summary of issues/concerns raised during the session. "
            "Detailed per-stakeholder concerns live on StakeholderEngagement rows."
        ),
    )
    summary_of_responses: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Summary of how the GRM Unit/implementing agency responded to issues.",
    )
    action_items: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            'Structured action items from the session. '
            'Example: {"items": [{"action": "Share design drawings", "by": "GRM Unit", "by_date": "2025-06-01"}]}'
        ),
    )
    minutes_url: Optional[str] = Field(
        default=None, max_length=1024, nullable=True,
        description="URL to the official meeting minutes document (CDN/S3).",
    )
    photos_urls: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='JSONB array of photo URLs: {"urls": ["https://cdn.riviwa.com/..."]}',
    )

    # ── Who ran it ────────────────────────────────────────────────────────────
    conducted_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the facilitator/GRM Unit staff who ran this session.",
    )
    cancelled_reason: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # project relationship intentionally omitted — project_id has no FK to the projects
    # table. Queries use explicit WHERE clauses on project_id instead.

    attendances: List["StakeholderEngagement"] = Relationship(
        back_populates="activity",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    media: List["ActivityMedia"] = Relationship(
        back_populates="activity",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_conducted(self) -> bool:
        return self.status == ActivityStatus.CONDUCTED

    def attendance_rate(self) -> Optional[float]:
        """Returns attendance rate 0.0–1.0 if both counts are set."""
        if self.expected_count and self.actual_count:
            return min(self.actual_count / self.expected_count, 1.0)
        return None

    def __repr__(self) -> str:
        return (
            f"<EngagementActivity {self.title!r} "
            f"[{self.activity_type}/{self.status}] "
            f"stage={self.stage}>"
        )



class StakeholderEngagement(SQLModel, table=True):
    """
    Junction: StakeholderContact ↔ EngagementActivity.

    Records the participation of a specific contact person in a specific
    activity, along with concerns they raised and the response given.

    WHY CONTACT-LEVEL (not stakeholder-level)?
    ──────────────────────────────────────────────────────────────────────────
    A stakeholder entity (e.g. M18 community) may send multiple contacts to
    an activity. Each contact may raise different concerns. Tracking at the
    contact level gives a complete picture of who said what.

    UNIQUE (contact_id, activity_id) — a contact can only attend an activity once.
    If multiple contacts from the same stakeholder attend, there will be one
    row per contact.

    Relationship wiring:
      StakeholderEngagement.activity  ←→  EngagementActivity.attendances
      StakeholderEngagement.contact   ←→  StakeholderContact.engagements
    """
    __tablename__ = "stakeholder_engagements"

    __table_args__ = (
        UniqueConstraint("contact_id", "activity_id", name="uq_contact_activity"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    contact_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("stakeholder_contacts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    activity_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("engagement_activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Attendance ────────────────────────────────────────────────────────────
    attendance_status: AttendanceStatus = Field(
        default=AttendanceStatus.ATTENDED,
        sa_column=Column(
            SAEnum(AttendanceStatus, name="attendance_status"),
            nullable=False,
        ),
    )
    proxy_name: Optional[str] = Field(
        default=None, max_length=200, nullable=True,
        description="Name of the delegate if attendance_status=REPRESENTED.",
    )

    # ── Concerns and responses ────────────────────────────────────────────────
    concerns_raised: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Issues, concerns, questions, or suggestions raised by this contact "
            "during the session. Captured verbatim or as a summary."
        ),
    )
    response_given: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="How the GRM Unit/facilitator responded to the concerns raised.",
    )
    feedback_submitted: bool = Field(
        default=False,
        nullable=False,
        description=(
            "True when concerns raised here were formally submitted as a "
            "feedback/grievance in feedback_service. "
            "Used to prevent double-counting and to link the consultation to the grievance."
        ),
    )
    feedback_ref_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description=(
            "feedback_service Feedback.id — set when concerns from this engagement "
            "were escalated to a formal feedback submission."
        ),
    )

    # ── Additional notes ──────────────────────────────────────────────────────
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    logged_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the GRM Unit staff who logged this attendance record.",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    activity: "EngagementActivity" = Relationship(back_populates="attendances")
    contact:  "StakeholderContact" = Relationship(back_populates="engagements")

    def __repr__(self) -> str:
        return (
            f"<StakeholderEngagement "
            f"contact={self.contact_id} "
            f"activity={self.activity_id} "
            f"status={self.attendance_status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Activity Media (meeting documents, photos, presentations)
# ─────────────────────────────────────────────────────────────────────────────

class MediaType(str, Enum):
    """
    Type of media file attached to a meeting / engagement activity.

    MINUTES:      Official signed meeting minutes (PDF).
    PHOTO:        Site or event photo (JPEG, PNG, WebP).
    PRESENTATION: Slide deck or presentation document (PDF, PPTX).
    DOCUMENT:     Any other supporting document (PDF, DOCX, XLSX).
    OTHER:        Any other file type.
    """
    MINUTES      = "minutes"
    PHOTO        = "photo"
    PRESENTATION = "presentation"
    DOCUMENT     = "document"
    OTHER        = "other"


class ActivityMedia(SQLModel, table=True):
    """
    A single media file (photo, PDF minutes, presentation) attached to an
    engagement activity.

    Replaces the flat `photos_urls` JSONB blob and `minutes_url` string on
    EngagementActivity with a proper per-file table that supports:
      · title and description per file
      · media type classification
      · upload metadata (who, when)
      · soft delete (file preserved in object storage as evidence)

    Object-storage path (MinIO/S3)
    ──────────────────────────────
    activities/{activity_id}/media/{id}.{ext}

    Note: EngagementActivity.photos_urls and minutes_url are kept for
    backward compatibility but ActivityMedia is the authoritative source
    for new uploads.
    """
    __tablename__ = "activity_media"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, nullable=False
    )

    activity_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("engagement_activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="The engagement activity this file belongs to.",
    )

    # ── File ──────────────────────────────────────────────────────────────────
    media_type: MediaType = Field(
        default=MediaType.DOCUMENT,
        sa_column=Column(SAEnum(MediaType, name="media_type"), nullable=False, index=True),
    )
    file_url: str = Field(
        sa_column=Column(Text, nullable=False),
        description=(
            "Permanent URL to the uploaded file in MinIO/S3. "
            "Path: activities/{activity_id}/media/{id}.{ext}. "
            "Never deleted — part of the engagement evidence trail."
        ),
    )
    file_name: Optional[str] = Field(
        default=None, max_length=255, nullable=True,
        description="Original filename as uploaded by the user.",
    )
    file_size_bytes: Optional[int] = Field(
        default=None, nullable=True,
        description="File size in bytes — stored for display in UI.",
    )
    mime_type: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="MIME type e.g. 'application/pdf', 'image/jpeg'.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    title: str = Field(
        max_length=300, nullable=False,
        description=(
            "Short descriptive title. Required. "
            "e.g. 'Meeting Minutes — Jangwani Consultation 2025-06-15' or "
            "'Site visit photo — Flood control works KM 24+300'."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Detailed description of the file's content.",
    )

    # ── Authorship ────────────────────────────────────────────────────────────
    uploaded_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the person who uploaded this file.",
    )
    uploaded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description=(
            "Soft-delete timestamp. The file in object storage is NEVER deleted — "
            "it forms part of the engagement evidence trail required by the SEP."
        ),
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    activity: "EngagementActivity" = Relationship(back_populates="media")

    def is_visible(self) -> bool:
        return self.deleted_at is None

    def __repr__(self) -> str:
        return (
            f"<ActivityMedia {self.media_type} "
            f"activity={self.activity_id} "
            f"title={self.title!r}>"
        )
