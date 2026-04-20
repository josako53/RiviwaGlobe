# ───────────────────────────────────────────────────────────────────────────
# SERVICE   :  stakeholder_service
# PORT      :  Port: 8070
# DATABASE  :  DB: stakeholder_db (5436)
# FILE      :  models/communication.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/communication.py
═══════════════════════════════════════════════════════════════════════════════
Three tables covering the full communication lifecycle.

  CommunicationRecord        → every outgoing or incoming communication logged
  CommunicationDistribution  → what happened AFTER a contact received a comm
  FocalPerson                → named GRM Unit contact per LGA/TANROADS/PO-RALG (SEP Table 9)

THE COMMUNICATION LIFECYCLE
──────────────────────────────────────────────────────────────────────────────

  1. GRM Unit sends a notice to M18 community (stakeholder entity)
     → CommunicationRecord created
       direction=OUTGOING, channel=LETTER
       stakeholder_id=M18, contact_id=Chairperson

  2. Chairperson receives it and distributes at the baraza
     → CommunicationDistribution created
       distributed_to_count=120, method=PUBLIC_MEETING
       concerns_raised_after="3 members asked about compensation timeline"

  3. M18 community sends a written response to GRM Unit
     → CommunicationRecord created
       direction=INCOMING, channel=LETTER
       stakeholder_id=M18, contact_id=Chairperson
       in_response_to_id=(id of the original outgoing record)

  4. If concerns_raised_after are serious enough → filed as Grievance
     in feedback_service. The feedback_ref_id is stored on the
     CommunicationDistribution row to link them.

WHY CommunicationDistribution MATTERS FOR COMPLIANCE
──────────────────────────────────────────────────────────────────────────────
  The SEP requires the GRM Unit to demonstrate that information ACTUALLY REACHED
  communities, not just that it was sent to the contact person. The
  distribution row provides this audit trail:
    - "We sent it to the Chairperson on 2025-06-01"  (CommunicationRecord)
    - "Chairperson distributed to 120 households on 2025-06-03 at baraza"
      (CommunicationDistribution)
  This is the evidence base for World Bank monitoring missions.

FOCAL PERSON (SEP Table 9)
──────────────────────────────────────────────────────────────────────────────
  The SEP mandates a named focal person at each implementing LGA, TANROADS,
  and PO-RALG. This table captures those named contacts so the system can
  route communications and grievances to the right person.
  FocalPersons are distinct from StakeholderContacts — they are GRM Unit STAFF,
  not stakeholder representatives.
═══════════════════════════════════════════════════════════════════════════════
"""
# NOTE: do NOT add `from __future__ import annotations` here.
# It stringifies all annotations at import time, which breaks SQLModel's
# List["Model"] relationship resolution.
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

# Runtime imports — SQLAlchemy mapper needs to resolve Relationship strings.
from models.project import ProjectCache, ProjectStageCache    # noqa: F401



class CommChannel(str, Enum):
    """
    The medium through which a communication was delivered or received.
    Drives monitoring reports — the SEP requires tracking which channels
    were used to reach different stakeholder groups.
    """
    EMAIL          = "email"
    SMS            = "sms"
    LETTER         = "letter"
    PHONE_CALL     = "phone_call"
    IN_PERSON      = "in_person"
    PUBLIC_MEETING = "public_meeting"
    RADIO          = "radio"
    TV             = "tv"
    SOCIAL_MEDIA   = "social_media"
    BILLBOARD      = "billboard"
    NOTICE_BOARD   = "notice_board"
    WEBSITE        = "website"
    NEWSPAPER      = "newspaper"
    FLYER_POSTER   = "flyer_poster"
    WHATSAPP_GROUP = "whatsapp_group"
    OTHER          = "other"


class CommDirection(str, Enum):
    OUTGOING = "outgoing"   # GRM Unit/implementing agency → stakeholder
    INCOMING = "incoming"   # stakeholder → GRM Unit/implementing agency


class CommPurpose(str, Enum):
    """
    Why this communication was sent — for categorisation and reporting.
    """
    INFORMATION_DISCLOSURE = "information_disclosure"   # sharing project documents
    MEETING_INVITATION     = "meeting_invitation"        # invite to consultation
    MEETING_MINUTES        = "meeting_minutes"           # post-meeting summary
    GRIEVANCE_RESPONSE     = "grievance_response"        # formal response to a complaint
    PROGRESS_UPDATE        = "progress_update"           # project status update
    COMPENSATION_NOTICE    = "compensation_notice"       # RAP/resettlement update
    GENERAL_INQUIRY        = "general_inquiry"           # incoming question
    COMPLAINT              = "complaint"                 # incoming complaint (pre-GRM)
    SUGGESTION             = "suggestion"                # incoming suggestion
    ACKNOWLEDGEMENT        = "acknowledgement"           # receipt confirmation
    OTHER                  = "other"


class DistributionMethod(str, Enum):
    """
    How a contact distributed a received communication to their broader group.
    Supports the SEP monitoring requirement to prove information reached communities.
    """
    VERBAL          = "verbal"          # announced at a meeting/baraza
    NOTICE_BOARD    = "notice_board"    # posted on community notice board
    WHATSAPP_GROUP  = "whatsapp_group"  # forwarded to a group chat
    PUBLIC_MEETING  = "public_meeting"  # presented at a community meeting
    SMS_BLAST       = "sms_blast"       # forwarded via SMS to group members
    DOOR_TO_DOOR    = "door_to_door"    # delivered individually to households
    RADIO           = "radio"           # announced on local radio
    PRINTED_COPIES  = "printed_copies"  # physical copies distributed
    OTHER           = "other"


class FocalPersonOrgType(str, Enum):
    """Type of implementing organisation the focal person is from."""
    LGA       = "lga"
    TANROADS  = "tanroads"
    PO_RALG   = "po_ralg"
    GRM_UNIT  = "grm_unit"
    TARURA    = "tarura"
    OTHER     = "other"



class CommunicationRecord(SQLModel, table=True):
    """
    Every outgoing and incoming communication logged for a project.

    OUTGOING examples:
      · Disclosure letter sent to M18 community leaders
      · Meeting invitation emailed to TANESCO
      · Progress update SMS blasted to ward contacts
      · Notice board poster placed at Mtaa office

    INCOMING examples:
      · Written response from NGO questioning compensation rates
      · Phone call from ward executive officer requesting project timelines
      · Walk-in complaint from a landowner

    The `in_response_to_id` field creates a thread — an incoming
    communication can reference the outgoing one it replies to,
    and vice versa.

    `stakeholder_id` and `contact_id` are both nullable:
      · Bulk/broadcast communications address all stakeholders → both null
      · Entity-level communications → stakeholder_id set, contact_id null
      · Contact-level communications → both set
    """
    __tablename__ = "communication_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    project_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Who ────────────────────────────────────────────────────────────────────
    # Nullable because some comms are broadcast to all stakeholders
    stakeholder_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description="Stakeholder entity this comm was addressed to. Null for broadcast comms.",
    )
    contact_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("stakeholder_contacts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="Specific contact who sent/received this comm. Null for entity-level or broadcast.",
    )

    # ── Classification ─────────────────────────────────────────────────────────
    channel:   CommChannel   = Field(
        sa_column=Column(SAEnum(CommChannel,   name="comm_channel"),   nullable=False, index=True)
    )
    direction: CommDirection = Field(
        sa_column=Column(SAEnum(CommDirection, name="comm_direction"),  nullable=False, index=True)
    )
    purpose:   CommPurpose   = Field(
        sa_column=Column(SAEnum(CommPurpose,   name="comm_purpose"),    nullable=False, index=True)
    )

    # ── Content ────────────────────────────────────────────────────────────────
    subject:         str           = Field(max_length=500, nullable=False)
    content_summary: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Summary of the communication content. "
            "Full documents are stored externally (CDN/S3) and referenced via document_urls."
        ),
    )
    document_urls: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='JSONB array of document URLs: {"urls": ["https://cdn.riviwa.com/..."]}',
    )

    # ── Threading ──────────────────────────────────────────────────────────────
    in_response_to_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            ForeignKey("communication_records.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description=(
            "Links this comm to a prior comm it responds to. "
            "Creates a simple thread without deep nesting."
        ),
    )

    # ── Distribution expectation ───────────────────────────────────────────────
    distribution_required: bool = Field(
        default=False,
        nullable=False,
        description=(
            "True when the receiving contact is expected to distribute this "
            "communication to their broader group. "
            "Triggers a CommunicationDistribution record requirement for monitoring."
        ),
    )
    distribution_deadline: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Deadline by which distribution must be completed and logged.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    sent_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the GRM Unit staff who sent/logged this comm.",
    )
    sent_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    received_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the incoming communication was received (for INCOMING direction).",
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the receiving contact confirmed receipt.",
    )

    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

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

    # ── Relationships ──────────────────────────────────────────────────────────
    project: "ProjectCache" = Relationship(back_populates="communications")
    contact: "StakeholderContact" = Relationship(
        back_populates=None,   # StakeholderContact does not back-populate comms (too many)
    )
    distributions: List["CommunicationDistribution"] = Relationship(
        back_populates="communication",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return (
            f"<CommunicationRecord {self.subject!r} "
            f"[{self.direction}/{self.channel}] "
            f"project={self.project_id}>"
        )



class CommunicationDistribution(SQLModel, table=True):
    """
    Tracks what happened AFTER a contact received a communication.

    This is the critical compliance bridge between "we sent it to the
    contact person" and "it actually reached the community."

    The World Bank monitoring mission will ask: how do you know the
    community received the information? The answer is this table.

    Key workflow:
      1. GRM Unit sends notice → CommunicationRecord (outgoing)
      2. Contact distributes it → CommunicationDistribution logged
         · Who: contact_id
         · How many: distributed_to_count (e.g. 120 households)
         · By what means: distribution_method (e.g. PUBLIC_MEETING)
         · When: distributed_at
         · What happened: concerns_raised_after (new issues surfaced)

      3. If concerns_raised_after are serious →
         feedback_service Feedback row created.
         feedback_ref_id stored here to link the distribution to the
         formal feedback submission.

    UNIQUE (communication_id, contact_id) —
      A contact can only have one distribution record per communication.
      If they distributed it in multiple ways, capture both in
      distribution_method (OTHER) and describe in distribution_notes.
    """
    __tablename__ = "communication_distributions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    communication_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("communication_records.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    contact_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("stakeholder_contacts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Distribution details ──────────────────────────────────────────────────
    distributed_to_count: Optional[int] = Field(
        default=None,
        nullable=True,
        description=(
            "Number of people/households the contact distributed to. "
            "Can be an estimate for community announcements."
        ),
    )
    distribution_method: DistributionMethod = Field(
        sa_column=Column(SAEnum(DistributionMethod, name="distribution_method"), nullable=False)
    )
    distribution_notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Narrative description of the distribution. "
            "e.g. 'Posted on ward notice board and announced at Friday baraza. "
            "47 households represented, 3 asked about compensation.'"
        ),
    )
    distributed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the contact distributed the communication.",
    )

    # ── Confirmation ──────────────────────────────────────────────────────────
    acknowledged_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the GRM Unit confirmed the distribution was completed.",
    )
    acknowledged_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the GRM Unit staff who confirmed distribution.",
    )

    # ── Post-distribution concerns ────────────────────────────────────────────
    concerns_raised_after: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Issues or concerns raised by community members AFTER the distribution. "
            "These may be distinct from concerns in the original consultation. "
            "If serious, they should be submitted as a Feedback/Grievance."
        ),
    )

    # ── Link to formal feedback submission ────────────────────────────────────
    feedback_ref_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description=(
            "feedback_service Feedback.id — set when concerns_raised_after "
            "were escalated to a formal feedback/grievance submission. "
            "Soft link — no FK constraint across service boundaries."
        ),
    )

    logged_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id who logged this distribution record.",
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

    # ── Relationships ──────────────────────────────────────────────────────────
    communication: "CommunicationRecord" = Relationship(back_populates="distributions")
    contact: "StakeholderContact"         = Relationship(back_populates="distributions")

    def is_confirmed(self) -> bool:
        return self.acknowledged_at is not None

    def has_pending_concerns(self) -> bool:
        return bool(self.concerns_raised_after) and self.feedback_ref_id is None

    def __repr__(self) -> str:
        return (
            f"<CommunicationDistribution "
            f"comm={self.communication_id} "
            f"contact={self.contact_id} "
            f"count={self.distributed_to_count}>"
        )



class FocalPerson(SQLModel, table=True):
    """
    Named focal contact at each implementing agency for a project.

    This is SEP Table 9 — "Proposed format of contacts details of the focal
    person at the LGA/TANROADS/PO-RALG".

    IMPORTANT DISTINCTION FROM StakeholderContact:
      · StakeholderContact = representative of a stakeholder ENTITY
        (community leader, NGO spokesperson) — they speak FOR stakeholders
      · FocalPerson = GRM Unit/implementing agency STAFF member who handles SEP
        (community development officer, public relations officer)
        — they speak FOR the project/implementing agency

    Every LGA implementing a subproject should have a named focal person.
    TANROADs and PO-RALG also have their own focal persons.

    The focal person is the first point of contact for:
      · Stakeholder inquiries
      · Grievance registration (from walk-ins, phone, letters)
      · Communication distribution coordination
      · SEP reporting upward to GRM Unit

    Relationship wiring:
      FocalPerson.project  ←→  Project.focal_persons
    """
    __tablename__ = "focal_persons"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    project_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Organisation they represent ────────────────────────────────────────────
    org_type: FocalPersonOrgType = Field(
        sa_column=Column(SAEnum(FocalPersonOrgType, name="focal_person_org_type"), nullable=False, index=True)
    )
    organization_name: str = Field(
        max_length=255,
        nullable=False,
        description="Full name of the LGA/agency e.g. 'Ilala Municipal Council'",
    )

    # ── Personal details (from SEP Table 9) ────────────────────────────────────
    title:     Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Job title e.g. 'Community Development Officer', 'Public Relations Officer'",
    )
    full_name: Optional[str] = Field(
        default=None, max_length=200, nullable=True,
        description="To be determined at project start — may be blank initially.",
    )
    phone:     Optional[str] = Field(default=None, max_length=20,  nullable=True)
    email:     Optional[str] = Field(default=None, max_length=255, nullable=True)
    address:   Optional[str] = Field(default=None, max_length=500, nullable=True)

    # ── Link to auth_service User ─────────────────────────────────────────────
    # Optional — set when this focal person has a Riviwa platform account.
    user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id — set when focal person has a Riviwa account.",
    )

    # ── Scope ─────────────────────────────────────────────────────────────────
    lga:         Optional[str] = Field(default=None, max_length=100, nullable=True)
    subproject:  Optional[str] = Field(default=None, max_length=255, nullable=True,
                                        description="Specific subproject this person is responsible for (if sub-project level).")

    is_active: bool = Field(default=True, nullable=False, index=True)
    notes:     Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

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

    # ── Relationships ──────────────────────────────────────────────────────────
    project: "ProjectCache" = Relationship(back_populates="focal_persons")

    def __repr__(self) -> str:
        return (
            f"<FocalPerson {self.full_name or 'TBD'!r} "
            f"[{self.org_type}] "
            f"org={self.organization_name!r}>"
        )
