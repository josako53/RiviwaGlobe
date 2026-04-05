# ───────────────────────────────────────────────────────────────────────────
# SERVICE   :  stakeholder_service
# PORT      :  Port: 8070
# DATABASE  :  DB: stakeholder_db (5436)
# FILE      :  models/stakeholder.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/stakeholder.py
═══════════════════════════════════════════════════════════════════════════════
Two tables — the entity and its human representatives.

THE CORE DISTINCTION
──────────────────────────────────────────────────────────────────────────────

  Stakeholder      → the ENTITY
    An NGO, a flood-prone community group, a ward committee, a government
    parastatal, a religious institution. This row never changes even when
    representatives rotate. It answers "WHO is affected or interested?"

  StakeholderContact → the PERSON (representative of the entity)
    The actual human who receives information, attends meetings, files
    grievances, and distributes communications to their community.
    Multiple contacts can exist per stakeholder. They can rotate without
    the stakeholder record changing.

WHY NOT JUST USE auth_service ORGANISATION?
──────────────────────────────────────────────────────────────────────────────
  Organisation (auth_service) = an entity that self-registers to TRANSACT
    on the Riviwa marketplace. It has an org dashboard, lists services,
    manages billing, receives payments.

  Stakeholder (this service) = an entity IDENTIFIED BY PROJECT STAFF because
    it is affected by or interested in a specific project. It is registered
    by the PIU, not by the entity itself. Most stakeholders will never have
    a Riviwa account.

  Some entities are BOTH — e.g. TANESCO is a Riviwa Organisation AND a
  Stakeholder in the Msimbazi project. The `org_id` soft link handles this.

SOFT LINKS TO AUTH_SERVICE
──────────────────────────────────────────────────────────────────────────────
  Stakeholder.org_id           → auth_service Organisation.id (optional)
  StakeholderContact.user_id   → auth_service User.id (optional)

  These are NOT foreign key constraints — they are application-layer soft
  links. No cross-service FK enforcement. Integrity is maintained by the
  service layer at write time and by consuming Kafka events when orgs/users
  are deactivated.

RELATIONSHIPS (all within this service)
──────────────────────────────────────────────────────────────────────────────
  Stakeholder.contacts              → StakeholderContact (representatives)
  Stakeholder.stakeholder_projects  → StakeholderProject (per-project registration)
  StakeholderContact.engagements    → StakeholderEngagement (activity attendance)
  StakeholderContact.distributions  → CommunicationDistribution (what they forwarded)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

# Runtime imports — SQLAlchemy mapper needs to resolve Relationship strings.
from models.project import ProjectCache, ProjectStageCache    # noqa: F401

if TYPE_CHECKING:
    from models.engagement import StakeholderEngagement
    from models.communication import CommunicationDistribution



class StakeholderType(str, Enum):
    """
    Classification based on relationship to the project.

    PAP (Project Affected Party):
      Directly or indirectly affected by project activities.
      Must be consulted, informed, and have grievance access.
      Examples: flood-prone community, utility firms, landowners.

    INTERESTED_PARTY:
      Has an interest in the project or can influence its outcome.
      Not necessarily directly affected.
      Examples: World Bank, ministries, MPs, NGOs, media.
    """
    PAP              = "pap"
    INTERESTED_PARTY = "interested_party"


class EntityType(str, Enum):
    """
    Structural type of the stakeholder entity.

    INDIVIDUAL: A single named person affected in their own right
      (not representing an org). E.g. a landowner, a sole trader.

    ORGANIZATION: A formally constituted entity — registered NGO,
      government ministry, private company, utility provider.

    GROUP: An informal collective — a community group, a ward
      residents' association, the M18 flood community leaders.
      No formal registration but acts as a unit.
    """
    INDIVIDUAL   = "individual"
    ORGANIZATION = "organization"
    GROUP        = "group"


class AffectednessType(str, Enum):
    """
    How the stakeholder is affected by the project.
    A single entity can be both — e.g. a community that gains flood
    protection (positive) but loses land for construction (negative).
    """
    POSITIVELY_AFFECTED = "positively_affected"
    NEGATIVELY_AFFECTED = "negatively_affected"
    BOTH                = "both"
    UNKNOWN             = "unknown"


class StakeholderCategory(str, Enum):
    """
    Category for filtering and applying appropriate engagement strategies.
    Based on the SEP stakeholder analysis framework.

    PRIMARY CATEGORIES (directly map to the SEP identified groups):
      INDIVIDUAL           → A named private person (landowner, sole trader, resident)
      LOCAL_GOVERNMENT     → Local Government Authorities (Ilala MC, Kinondoni MC, Ward office)
      NATIONAL_GOVERNMENT  → Central government ministries, agencies, regulatory bodies
      NGO_CBO              → NGOs, CBOs, CSOs, Faith-Based Organisations, Workers Unions
      COMMUNITY_GROUP      → Informal community groups (M18 leaders, Ward residents association)
      PRIVATE_COMPANY      → Commercial businesses, contractors, private sector entities
      UTILITY_PROVIDER     → TANESCO, DAWASA, TTCL, telecom companies, utility regulators
      DEVELOPMENT_PARTNER  → World Bank, USAID, bilateral donors, multilateral agencies
      MEDIA                → Print, broadcast, online media
      ACADEMIC_RESEARCH    → Universities, research institutions, think tanks
      VULNERABLE_GROUP     → Groups defined primarily by their vulnerability status
      OTHER                → Any entity not fitting above categories
    """
    INDIVIDUAL          = "individual"
    LOCAL_GOVERNMENT    = "local_government"
    NATIONAL_GOVERNMENT = "national_government"
    NGO_CBO             = "ngo_cbo"
    COMMUNITY_GROUP     = "community_group"
    PRIVATE_COMPANY     = "private_company"
    UTILITY_PROVIDER    = "utility_provider"
    DEVELOPMENT_PARTNER = "development_partner"
    MEDIA               = "media"
    ACADEMIC_RESEARCH   = "academic_research"
    VULNERABLE_GROUP    = "vulnerable_group"
    OTHER               = "other"


class ImportanceRating(str, Enum):
    """
    Importance / influence rating for prioritising engagement effort.

    Determined by the PIU based on two axes from the SEP stakeholder analysis:
      · Level of influence on the project outcome
      · Level of impact the project has on them

    HIGH    → High influence OR highly impacted (or both).
              Requires frequent, direct, and personalised engagement.
              Examples: World Bank, flood-prone community PAPs, TANROADs,
              relevant line ministries, LGAs directly implementing subprojects.

    MEDIUM  → Moderate influence AND moderate impact.
              Standard engagement — included in all consultations, receives
              information disclosures, attends workshops.
              Examples: NGOs, CBOs, business community, ward committees.

    LOW     → Low influence AND low impact.
              Kept informed via general broadcast channels (radio, notice boards,
              website). Does not require direct engagement for every activity.
              Examples: distant communities, national media, academic bodies.

    Note: Rating can change over the project lifecycle — a LOW stakeholder
    during preparation may become HIGH during construction if they are near
    an active work site. PIU should review ratings at each project stage.
    """
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class VulnerableGroupType(str, Enum):
    """
    Types of vulnerability as defined in ESS 7 and ESS 10.
    A stakeholder can have multiple vulnerability types (stored as JSONB array).
    """
    CHILDREN             = "children"
    WOMEN_LOW_INCOME     = "women_low_income"
    DISABLED_PHYSICAL    = "disabled_physical"
    DISABLED_MENTAL      = "disabled_mental"
    ELDERLY              = "elderly"
    YOUTH                = "youth"
    LOW_INCOME           = "low_income"
    INDIGENOUS           = "indigenous"
    LANGUAGE_BARRIER     = "language_barrier"


class PreferredChannel(str, Enum):
    """
    How this stakeholder prefers to be contacted.
    Drives which communication strategy the PIU uses per the SEP.
    """
    PUBLIC_MEETING  = "public_meeting"
    FOCUS_GROUP     = "focus_group"
    EMAIL           = "email"
    SMS             = "sms"
    PHONE_CALL      = "phone_call"
    RADIO           = "radio"
    TV              = "tv"
    SOCIAL_MEDIA    = "social_media"
    BILLBOARD       = "billboard"
    NOTICE_BOARD    = "notice_board"
    LETTER          = "letter"
    IN_PERSON       = "in_person"



class Stakeholder(SQLModel, table=True):
    """
    The stakeholder entity — an NGO, community group, government body,
    private company, or individual affected by or interested in a project.

    This row represents WHO they are. It persists even when the people
    representing them (StakeholderContacts) change.

    Key design decisions:
      · org_id: soft link to auth_service Organisation — set when this
        stakeholder is also a registered Riviwa Organisation (e.g. TANESCO,
        DART). Null for community groups and entities not on the platform.
      · language_preference: drives translation requirements per SEP Table 2.
      · preferred_channel: drives engagement strategy per SEP Table 6.
      · vulnerable_group_types: JSONB array of VulnerableGroupType values.
        Null or empty = not classified as a vulnerable group.
    """
    __tablename__ = "stakeholders"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── Entity type and classification ────────────────────────────────────────
    stakeholder_type: StakeholderType = Field(
        sa_column=Column(
            SAEnum(StakeholderType, name="stakeholder_type"),
            nullable=False,
            index=True,
        ),
    )
    entity_type: EntityType = Field(
        sa_column=Column(
            SAEnum(EntityType, name="entity_type"),
            nullable=False,
            index=True,
        ),
    )
    category: StakeholderCategory = Field(
        sa_column=Column(
            SAEnum(StakeholderCategory, name="stakeholder_category"),
            nullable=False,
            index=True,
        ),
    )
    affectedness: AffectednessType = Field(
        default=AffectednessType.UNKNOWN,
        sa_column=Column(
            SAEnum(AffectednessType, name="affectedness_type"),
            nullable=False,
            index=True,
        ),
    )
    importance_rating: ImportanceRating = Field(
        default=ImportanceRating.MEDIUM,
        sa_column=Column(
            SAEnum(ImportanceRating, name="importance_rating"),
            nullable=False,
            index=True,
        ),
        description=(
            "PIU-assigned importance rating: HIGH / MEDIUM / LOW. "
            "Drives engagement frequency and channel selection. "
            "Should be reviewed at each project stage as influence and impact can shift."
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    # For ORGANIZATION / GROUP: use org_name (individual's name goes in first_name/last_name)
    # For INDIVIDUAL: use first_name + last_name; org_name is null
    org_name:   Optional[str] = Field(
        default=None, max_length=255, nullable=True, index=True,
        description="Organisation or group name. Null for individual stakeholders.",
    )
    first_name: Optional[str] = Field(default=None, max_length=100, nullable=True)
    last_name:  Optional[str] = Field(default=None, max_length=100, nullable=True)

    # ── Soft link to auth_service Organisation ────────────────────────────────
    # Set when this stakeholder is also a registered Riviwa Organisation.
    # NOT a FK constraint — application-layer soft link only.
    org_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "auth_service Organisation.id — set when this stakeholder is also a "
            "Riviwa Organisation (e.g. TANESCO, DART, an NGO registered on the platform). "
            "Null for community groups and entities without a Riviwa account."
        ),
    )

    # ── Address (cross-service soft link) ─────────────────────────────────────
    # The full address lives in auth_service's `addresses` table.
    # stakeholder_service stores only the UUID — no FK constraint across
    # service boundaries.
    #
    # Workflow:
    #   1. PIU staff calls auth_service POST /api/v1/addresses with
    #      entity_type="stakeholder", entity_id=<stakeholder_id>
    #   2. auth_service creates the Address row and returns address.id
    #   3. stakeholder_service stores that UUID here
    #
    # When an Address is deleted in auth_service, it publishes
    # address.deleted on riviwa.org.events → stakeholder_service consumer
    # nulls out this field.
    #
    # `lga` and `ward` are denormalised here for fast geographic filtering
    # queries (e.g. "all stakeholders in Ilala ward Jangwani") without
    # requiring a cross-service address lookup. They must be kept in sync
    # whenever the Address record is updated.
    #
    address_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "Soft link to auth_service Address.id (entity_type='stakeholder'). "
            "NOT a FK constraint — application-layer link only."
        ),
    )
    # Denormalised for local filtering — mirrors Address.lga / Address.ward
    lga:  Optional[str] = Field(default=None, max_length=100, nullable=True, index=True,
                                 description="Denormalised from Address.lga for fast geographic queries.")
    ward: Optional[str] = Field(default=None, max_length=100, nullable=True, index=True,
                                 description="Denormalised from Address.ward for fast geographic queries.")

    # ── Communication preferences ──────────────────────────────────────────────
    language_preference: str = Field(
        default="sw",
        max_length=10,
        nullable=False,
        description="BCP-47 language tag. 'sw' = Swahili (default), 'en' = English.",
    )
    preferred_channel: PreferredChannel = Field(
        default=PreferredChannel.PUBLIC_MEETING,
        sa_column=Column(
            SAEnum(PreferredChannel, name="preferred_channel"),
            nullable=False,
        ),
    )
    needs_translation: bool = Field(
        default=False,
        nullable=False,
        description="True if materials must be translated (sign language, local dialect, Braille, etc.)",
    )
    needs_transport:   bool = Field(
        default=False,
        nullable=False,
        description="True if transport to consultation venues must be provided.",
    )
    needs_childcare:   bool = Field(
        default=False,
        nullable=False,
        description="True if childcare at consultation venues must be arranged.",
    )

    # ── Vulnerability ─────────────────────────────────────────────────────────
    is_vulnerable: bool = Field(
        default=False,
        nullable=False,
        index=True,
        description=(
            "True when this stakeholder qualifies as a vulnerable group or individual "
            "under ESS 7 / ESS 10. Triggers specific engagement strategies per SEP."
        ),
    )
    vulnerable_group_types: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            'JSONB array of VulnerableGroupType values. '
            'Example: {"types": ["elderly", "disabled_physical"]}. '
            'Null or empty when is_vulnerable=False.'
        ),
    )
    participation_barriers: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Free-text description of participation limitations from the SEP: "
            "language barrier, transport limitations, cultural limitations, etc."
        ),
    )

    # ── Administrative ────────────────────────────────────────────────────────
    notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    registered_by_user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="auth_service User.id of the PIU staff member who registered this stakeholder.",
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
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Set on soft-delete; null while active.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    contacts: StakeholderContact = Relationship(
        back_populates="stakeholder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    stakeholder_projects: StakeholderProject = Relationship(
        back_populates="stakeholder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    stage_engagements: StakeholderStageEngagement = Relationship(
        back_populates="stakeholder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # ── Domain helpers ────────────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        """Best available display name for this stakeholder entity."""
        if self.org_name:
            return self.org_name
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return f"Stakeholder {str(self.id)[:8]}"

    def get_primary_contact(self) -> Optional["StakeholderContact"]:
        """Returns the primary contact if contacts are loaded."""
        for c in self.contacts:
            if c.is_primary and c.is_active:
                return c
        # Fallback: any active contact
        for c in self.contacts:
            if c.is_active:
                return c
        return None

    def is_active(self) -> bool:
        return self.deleted_at is None

    def __repr__(self) -> str:
        return (
            f"<Stakeholder {self.display_name!r} "
            f"[{self.stakeholder_type}/{self.category}]>"
        )



class StakeholderProject(SQLModel, table=True):
    """
    Registers a Stakeholder against a specific Project (OrgService).

    A stakeholder can be registered against multiple projects.
    A project can have many registered stakeholders.
    The affectedness and impact description may differ per project.

    UNIQUE (stakeholder_id, project_id) — one registration per pair.

    Relationship wiring:
      StakeholderProject.stakeholder  ←→  Stakeholder.stakeholder_projects
      StakeholderProject.project      ←→  Project.stakeholder_projects
    """
    __tablename__ = "stakeholder_projects"

    __table_args__ = (
        UniqueConstraint("stakeholder_id", "project_id", name="uq_stakeholder_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    stakeholder_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("stakeholders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # project_id is NOT a FK to projects table because this service
    # also needs to register stakeholders before the project syncs from Kafka.
    # Application layer validates project existence.
    project_id: uuid.UUID = Field(nullable=False, index=True)

    # ── Project-specific classification ───────────────────────────────────────
    is_pap: bool = Field(
        default=False,
        nullable=False,
        description=(
            "True when this stakeholder is a Project Affected Party (PAP) "
            "for this specific project. "
            "An entity can be PAP on one project and only Interested Party on another."
        ),
    )
    affectedness: Optional[AffectednessType] = Field(
        default=None,
        sa_column=Column(SAEnum(AffectednessType, name="affectedness_type"), nullable=True),
        description="Affectedness specific to this project (may differ from entity-level default).",
    )
    impact_description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Narrative description of how this stakeholder is affected by this "
            "specific project. Required for PAPs."
        ),
    )

    # ── Engagement stage tracking ─────────────────────────────────────────────
    # Records which project stage this stakeholder was first engaged at.
    first_engaged_stage: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
        description="EngagementStage value at which this stakeholder was first consulted.",
    )
    consultation_count: int = Field(
        default=0,
        nullable=False,
        description="Running count of engagement activities this stakeholder has attended.",
    )

    registered_at:         datetime           = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    registered_by_user_id: Optional[uuid.UUID] = Field(default=None, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    stakeholder: Stakeholder  = Relationship(back_populates="stakeholder_projects")
    project:     ProjectCache = Relationship(back_populates="stakeholder_projects")

    def __repr__(self) -> str:
        return (
            f"<StakeholderProject "
            f"stakeholder={self.stakeholder_id} "
            f"project={self.project_id} "
            f"pap={self.is_pap}>"
        )



class StakeholderContact(SQLModel, table=True):
    """
    A named person who represents a Stakeholder entity.

    WHY SEPARATE FROM STAKEHOLDER?
    ──────────────────────────────────────────────────────────────────────────
    The M18 community group (Stakeholder) persists forever. Their chairperson
    who receives communications (StakeholderContact) can change. The contact
    record is deactivated and a new one created — the stakeholder entity remains.

    An organisation can have MULTIPLE contacts:
      · Primary contact: receives formal disclosures and meeting invites
      · Secondary contact: backup; escalation point
      · Technical contact: for site visit coordination
      · GRM contact: specifically authorised to file/receive grievances

    LINK TO AUTH_SERVICE USER
    ──────────────────────────────────────────────────────────────────────────
    user_id is set when the contact has a Riviwa platform account.
    When set, this person can:
      · Log in and see all communications addressed to their stakeholder entity
      · Submit feedback/grievances via the API using their JWT
      · Mark communication distributions as complete
    When null (most contacts), PIU staff manually logs their activities.

    Relationship wiring:
      StakeholderContact.stakeholder   ←→  Stakeholder.contacts
      StakeholderContact.engagements   ←→  StakeholderEngagement.contact
      StakeholderContact.distributions ←→  CommunicationDistribution.contact
    """
    __tablename__ = "stakeholder_contacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # CASCADE: removing a Stakeholder removes all their contacts
    stakeholder_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("stakeholders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Soft link to auth_service User ────────────────────────────────────────
    # NOT a FK constraint — application-layer soft link.
    # Set when this contact has a Riviwa platform account.
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "auth_service User.id — set when this contact has a Riviwa account. "
            "When set, they can submit feedback via JWT-authenticated API calls."
        ),
    )

    # ── Personal details ──────────────────────────────────────────────────────
    full_name: str = Field(max_length=200, nullable=False)
    title:     Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Formal title e.g. 'Ward Executive Officer', 'Programme Director'",
    )
    role_in_org: Optional[str] = Field(
        default=None,
        max_length=200,
        nullable=True,
        description="Their role within the stakeholder entity e.g. 'Chairperson M18', 'Secretary General'",
    )

    # ── Contact details ────────────────────────────────────────────────────────
    email:  Optional[str] = Field(default=None, max_length=255, nullable=True)
    phone:  Optional[str] = Field(default=None, max_length=20,  nullable=True)
    preferred_channel: PreferredChannel = Field(
        default=PreferredChannel.PHONE_CALL,
        sa_column=Column(SAEnum(PreferredChannel, name="contact_preferred_channel"), nullable=False),
        description="How THIS contact prefers to be reached (may differ from stakeholder entity preference).",
    )

    # ── Authorisations ────────────────────────────────────────────────────────
    is_primary: bool = Field(
        default=False,
        nullable=False,
        description=(
            "Main point of contact for the stakeholder entity. "
            "Receives formal disclosures and meeting invitations."
        ),
    )
    can_submit_feedback: bool = Field(
        default=True,
        nullable=False,
        description=(
            "Authorised to submit feedback (including grievances) on behalf of the entity. "
            "True for primary and most secondary contacts."
        ),
    )
    can_receive_communications: bool = Field(
        default=True,
        nullable=False,
        description="Receives formal disclosure documents and meeting invites.",
    )
    can_distribute_communications: bool = Field(
        default=False,
        nullable=False,
        description=(
            "Responsible for distributing received communications to the broader group. "
            "True for community leaders and focal persons. "
            "When True, CommunicationDistribution records are expected after each outgoing comm."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: bool = Field(
        default=True,
        nullable=False,
        index=True,
        description="False when this contact is no longer the representative (left role, resigned, etc.).",
    )
    deactivated_at:     Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    deactivation_reason: Optional[str]     = Field(default=None, max_length=500, nullable=True)

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

    # ── Relationships ─────────────────────────────────────────────────────────
    stakeholder: Stakeholder = Relationship(back_populates="contacts")

    engagements: StakeholderEngagement = Relationship(
        back_populates="contact",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    distributions: CommunicationDistribution = Relationship(
        back_populates="contact",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return (
            f"<StakeholderContact {self.full_name!r} "
            f"stakeholder={self.stakeholder_id} "
            f"primary={self.is_primary}>"
        )



class StakeholderActivity(str, Enum):
    """
    Granular activities a stakeholder is permitted to perform in a given stage.
    Assigned per stage by project admins — different stages grant different permissions.

    EXAMPLES:
      World Bank in Preparation Stage:
        ATTEND_MEETINGS, GIVE_SUGGESTIONS, VIEW_REPORTS, REQUEST_REPORTS,
        VIEW_GRIEVANCES, RECEIVE_NOTIFICATIONS

      M18 Community in Construction Stage:
        ATTEND_MEETINGS, SUBMIT_GRIEVANCES, RECEIVE_NOTIFICATIONS,
        GIVE_SUGGESTIONS

      TANESCO in Construction Stage:
        ATTEND_MEETINGS, RECEIVE_NOTIFICATIONS, GIVE_SUGGESTIONS

      Platform moderator (always):
        VIEW_GRIEVANCES, RESOLVE_GRIEVANCES, GIVE_FEEDBACK
    """
    ATTEND_MEETINGS       = "attend_meetings"
    GIVE_SUGGESTIONS      = "give_suggestions"
    GIVE_APPLAUSE         = "give_applause"
    SUBMIT_GRIEVANCES     = "submit_grievances"
    VIEW_GRIEVANCES       = "view_grievances"
    COLLECT_GRIEVANCES    = "collect_grievances"    # on behalf of others (e.g. ward office)
    RESOLVE_GRIEVANCES    = "resolve_grievances"    # GHC members
    RECEIVE_NOTIFICATIONS = "receive_notifications"
    VIEW_REPORTS          = "view_reports"
    REQUEST_REPORTS       = "request_reports"
    GIVE_FEEDBACK         = "give_feedback"         # general feedback/comments
    PARTICIPATE_IN_SURVEYS = "participate_in_surveys"
    OBSERVE_SITE_VISITS   = "observe_site_visits"
    REVIEW_DOCUMENTS      = "review_documents"      # ESIAs, RAPs, design drawings


from sqlalchemy.dialects.postgresql import JSONB as _JSONB

class StakeholderStageEngagement(SQLModel, table=True):
    """
    Defines how a stakeholder participates in a specific project stage.

    This is the core of the SEP's stakeholder analysis per stage:
      · WHAT role does this stakeholder play in this stage?
      · HOW IMPORTANT are they to this stage's success?
      · WHAT ARE THEIR GOALS AND INTERESTS in this stage?
      · WHAT ACTIVITIES are they permitted to perform in this stage?

    KEY INSIGHT FROM THE SEP:
      The same stakeholder can have completely different importance, goals,
      and permitted activities across stages:

      World Bank:
        Preparation Stage     → CRITICAL, can request reports, give suggestions
        Construction Stage    → HIGH, can view grievances, receive notifications
        Finalization Stage    → CRITICAL, must approve completion reports

      Flood Community M18:
        Preparation Stage     → CRITICAL, must be consulted, can submit grievances
        Construction Stage    → HIGH, can submit grievances, attend meetings
        Operation Stage       → MEDIUM, receive notifications only

    UNIQUE (stakeholder_id, project_id, stage_id) — one record per
    stakeholder per stage per project.

    Relationship wiring:
      StakeholderStageEngagement.stakeholder  ←→  Stakeholder.stage_engagements
      StakeholderStageEngagement.stage        ←→  ProjectStageCache.stage_engagements
    """
    __tablename__ = "stakeholder_stage_engagements"

    __table_args__ = (
        UniqueConstraint(
            "stakeholder_id", "project_id", "stage_id",
            name="uq_stakeholder_stage_project",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    stakeholder_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("stakeholders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # project_id denormalised for efficient querying across all stage engagements
    project_id: uuid.UUID = Field(nullable=False, index=True)
    stage_id:   uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("project_stages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Importance rating (set by project owner/admin) ─────────────────────────
    importance: ImportanceRating = Field(
        default=ImportanceRating.MEDIUM,
        sa_column=Column(
            SAEnum(ImportanceRating, name="importance_rating"),
            nullable=False,
            index=True,
        ),
        description=(
            "How important this stakeholder is to this stage's success. "
            "Set by project owners/admins — not by the stakeholder themselves."
        ),
    )
    importance_justification: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Why this importance rating was assigned. For audit trail.",
    )

    # ── Stakeholder profile for this stage ────────────────────────────────────
    engagement_role: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Free-text description of this stakeholder's role in this stage. "
            "e.g. 'Fund provider and technical advisor' (World Bank), "
            "'Directly affected community requiring resettlement' (M18), "
            "'Utility infrastructure owner in construction zone' (TANESCO)."
        ),
    )
    goals: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "What this stakeholder wants to achieve in this stage. "
            "e.g. World Bank: 'Ensure ESS compliance and PDO achievement'. "
            "M18: 'Fair compensation, safe resettlement, return priority'."
        ),
    )
    interests: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "What this stakeholder is primarily concerned about in this stage. "
            "e.g. TANESCO: 'Safe relocation of power infrastructure, minimal outage'. "
            "Traffic Police: 'Traffic management plan during bridge construction'."
        ),
    )
    potential_risks: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Risks this stakeholder poses or faces in this stage. "
            "e.g. M18: 'Fear of not being compensated; risk of social opposition'. "
            "Councillors: 'Fear of losing voters; conflict of interests on PAP compensation'."
        ),
    )
    engagement_approach: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Recommended approach to engaging this stakeholder in this stage. "
            "Derived from the SEP's stakeholder analysis tables."
        ),
    )

    # ── Permitted activities (JSONB array of StakeholderActivity values) ───────
    allowed_activities: Optional[dict] = Field(
        default=None,
        sa_column=Column(_JSONB, nullable=True),
        description=(
            'JSONB array of permitted StakeholderActivity values for this stage. '
            'Example: {"activities": ["attend_meetings", "submit_grievances", "receive_notifications"]}. '
            'Null = no specific activities defined; defaults apply.'
        ),
    )

    # ── Notification preferences ───────────────────────────────────────────────
    notify_on_grievance_filed:    bool = Field(default=False, nullable=False)
    notify_on_grievance_resolved: bool = Field(default=False, nullable=False)
    notify_on_stage_milestone:    bool = Field(default=True,  nullable=False)
    notify_on_document_published: bool = Field(default=False, nullable=False)
    notify_channel: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
        description="Preferred notification channel for this stage (overrides entity-level preference).",
    )

    # ── Engagement frequency ──────────────────────────────────────────────────
    engagement_frequency: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description=(
            "How often this stakeholder should be engaged in this stage. "
            "e.g. 'Weekly during RAP implementation', 'Monthly during construction', "
            "'Quarterly during preparation'."
        ),
    )

    # ── Admin ────────────────────────────────────────────────────────────────
    rated_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the project admin who set this rating.",
    )
    is_active: bool = Field(default=True, nullable=False,
                             description="False if this engagement definition has been superseded.")

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
    stakeholder: Stakeholder = Relationship(back_populates="stage_engagements")
    stage: ProjectStageCache = Relationship(back_populates="stage_engagements")

    def has_activity(self, activity: str) -> bool:
        """Check if this stakeholder is permitted a specific activity in this stage."""
        if not self.allowed_activities:
            return False
        return activity in (self.allowed_activities.get("activities") or [])

    def __repr__(self) -> str:
        return (
            f"<StakeholderStageEngagement "
            f"stakeholder={self.stakeholder_id} "
            f"stage={self.stage_id} "
            f"importance={self.importance}>"
        )
