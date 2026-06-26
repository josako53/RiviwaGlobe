"""models/industry.py
═══════════════════════════════════════════════════════════════════════════════
Industry taxonomy and org–industry many-to-many relationship.

Tables
──────
  industries               — master list of industries (seeded, org-agnostic)
  organisation_industries  — M2M: which industries an org operates in
  org_custom_field_defs    — per-org custom field schema per entity type
  industry_field_templates — pre-built field sets per industry (from KB research)
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, Boolean, Integer, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class CustomFieldType(str, Enum):
    TEXT        = "text"
    TEXTAREA    = "textarea"
    NUMBER      = "number"
    DECIMAL     = "decimal"
    DATE        = "date"
    DATETIME    = "datetime"
    BOOLEAN     = "boolean"
    SELECT      = "select"
    MULTISELECT = "multiselect"
    PHONE       = "phone"
    EMAIL       = "email"
    URL         = "url"
    FILE_URL    = "file_url"
    CURRENCY    = "currency"
    RATING      = "rating"


class CustomFieldEntity(str, Enum):
    ORGANISATION = "organisation"
    FEEDBACK     = "feedback"
    STAKEHOLDER  = "stakeholder"
    DEPARTMENT   = "department"
    BRANCH       = "branch"
    SERVICE      = "service"
    PRODUCT      = "product"
    PROJECT      = "project"
    USER_PROFILE = "user_profile"


# ── Industry ──────────────────────────────────────────────────────────────────

class Industry(SQLModel, table=True):
    """Master list of industries. Platform-seeded; orgs select from this list."""
    __tablename__ = "industries"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    name: str = Field(
        max_length=150,
        nullable=False,
        description="e.g. 'Healthcare / Hospital', 'Finance / Banking'",
    )
    slug: str = Field(
        max_length=80,
        nullable=False,
        unique=True,
        description="URL-safe key e.g. 'healthcare', 'finance-banking'",
    )
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    icon_url: Optional[str] = Field(default=None, max_length=512)
    parent_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
    )

    # Relationships
    org_industries: list["OrganisationIndustry"] = Relationship(back_populates="industry")
    field_templates: list["IndustryFieldTemplate"] = Relationship(back_populates="industry")


# ── OrganisationIndustry (M2M junction) ──────────────────────────────────────

class OrganisationIndustry(SQLModel, table=True):
    """Many-to-many: an org can operate in multiple industries."""
    __tablename__ = "organisation_industries"
    __table_args__ = (
        UniqueConstraint("org_id", "industry_id", name="uq_org_industry"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    industry_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    is_primary: bool = Field(
        default=False,
        description="Mark the organisation's primary industry",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"))
    )

    # Relationships
    industry: Optional["Industry"] = Relationship(back_populates="org_industries")


# ── OrgCustomFieldDefinition ──────────────────────────────────────────────────

class OrgCustomFieldDefinition(SQLModel, table=True):
    """
    Per-org schema for custom fields on any entity type.

    An org admin creates these to capture industry-specific data.
    The AI service reads these to know which extra fields to collect
    during a feedback conversation.

    Example: A hospital org defines field_key='patient_file_number',
    entity_type='feedback', label='Patient File No.', required=True.
    The AI will then ask for the patient file number during any grievance
    conversation at that hospital.
    """
    __tablename__ = "org_custom_field_defs"
    __table_args__ = (
        UniqueConstraint("org_id", "entity_type", "field_key", name="uq_org_entity_field_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    entity_type: str = Field(
        max_length=30,
        nullable=False,
        description="Which entity carries this field: feedback | stakeholder | department | branch | service | product | project | organisation | user_profile",
    )
    field_key: str = Field(
        max_length=100,
        nullable=False,
        description="snake_case identifier e.g. 'patient_file_number', 'drug_batch_number'",
    )
    label: str = Field(
        max_length=200,
        nullable=False,
        description="Human-readable label e.g. 'Patient File Number'",
    )
    label_sw: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Swahili label e.g. 'Nambari ya Faili la Mgonjwa'",
    )
    field_type: str = Field(
        max_length=20,
        nullable=False,
        default="text",
        description="text | textarea | number | decimal | date | datetime | boolean | select | multiselect | phone | email | url | file_url | currency | rating",
    )
    options: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='For select/multiselect: {"choices": ["Option A", "Option B"]}',
    )
    placeholder: Optional[str] = Field(default=None, max_length=300)
    help_text: Optional[str] = Field(default=None, max_length=500)
    is_required: bool = Field(default=False)
    is_visible_to_consumer: bool = Field(
        default=True,
        description="Show in consumer-facing summary/receipt",
    )
    feedback_types: Optional[list] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='Which feedback types show this field: ["grievance", "suggestion"] or null=all',
    )
    industry_template_key: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Which industry template this was imported from e.g. 'healthcare'",
    )
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_by_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
    )


# ── IndustryFieldTemplate ─────────────────────────────────────────────────────

class IndustryFieldTemplate(SQLModel, table=True):
    """
    Pre-built custom field definitions per industry.

    When an org selects an industry, they can one-click import these templates
    into their OrgCustomFieldDefinition table. Seeded from the Riviwa KB research
    (KB_45-KB_73 — industry-specific feedback field standards).
    """
    __tablename__ = "industry_field_templates"
    __table_args__ = (
        UniqueConstraint("industry_id", "entity_type", "field_key", name="uq_industry_entity_field"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    industry_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    entity_type: str = Field(max_length=30, nullable=False)
    field_key: str = Field(max_length=100, nullable=False)
    label: str = Field(max_length=200, nullable=False)
    label_sw: Optional[str] = Field(default=None, max_length=200)
    field_type: str = Field(max_length=20, nullable=False, default="text")
    options: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    placeholder: Optional[str] = Field(default=None, max_length=300)
    help_text: Optional[str] = Field(default=None, max_length=500)
    is_required: bool = Field(default=False)
    is_visible_to_consumer: bool = Field(default=True)
    feedback_types: Optional[list] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    source_standard: Optional[str] = Field(
        default=None,
        max_length=200,
        description="e.g. 'WHO ICPS 2009', 'ISO 10002:2018', 'IFC PS5'",
    )
    sort_order: int = Field(default=0)

    # Relationships
    industry: Optional["Industry"] = Relationship(back_populates="field_templates")


# ── IndustryPolicyDocument ────────────────────────────────────────────────────

class PolicyDocumentType(str, Enum):
    LAW        = "LAW"         # Acts of Parliament, statutes
    REGULATION = "REGULATION"  # Statutory instruments, rules
    POLICY     = "POLICY"      # Government policy papers
    STANDARD   = "STANDARD"    # Industry standards (ISO, IEC, etc.)
    GUIDELINE  = "GUIDELINE"   # Best practice guidelines
    DIRECTIVE  = "DIRECTIVE"   # Directives / circulars
    FRAMEWORK  = "FRAMEWORK"   # Operational frameworks


class IndustryPolicyDocument(SQLModel, table=True):
    """
    Country-level or platform-wide industry policy, law, regulation, or standard.

    Examples:
      - Tanzania Food Safety Act, 2003 (industry=food, country_code=TZ, type=LAW)
      - ISO 9001:2015 Quality Management (industry=NULL=all, type=STANDARD)
      - WHO Guidelines on Safe Medication Practices (type=GUIDELINE)
      - IFC Performance Standard 5 (type=FRAMEWORK)

    industry_id = NULL → applies to all industries (platform-wide)
    country_code = NULL → international / not country-specific
    """
    __tablename__ = "industry_policy_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    industry_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="NULL = applies to all industries (platform-wide)",
    )

    country_code: Optional[str] = Field(
        default=None, max_length=3, nullable=True, index=True,
        description="ISO 3166-1 alpha-2/3 e.g. 'TZ', 'KE'. NULL = international.",
    )
    region: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Sub-national region e.g. 'East Africa', 'Dar es Salaam'",
    )

    policy_type: PolicyDocumentType = Field(
        sa_column=Column(SAEnum(PolicyDocumentType, name="policy_document_type"),
                         nullable=False, index=True),
    )

    title:              str           = Field(max_length=500, nullable=False)
    slug:               str           = Field(max_length=200, nullable=False, unique=True, index=True,
                                              description="URL-safe handle e.g. 'tz-food-safety-act-2003'")
    issuing_authority:  Optional[str] = Field(default=None, max_length=300, nullable=True,
                                              description="e.g. 'Government of Tanzania', 'ISO', 'WHO'")
    document_number:    Optional[str] = Field(default=None, max_length=100, nullable=True,
                                              description="e.g. 'ISO 9001:2015', 'Cap. 432'")

    effective_date: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    expiry_date: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    content_md: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Full text or summary in Markdown",
    )
    file_url:   Optional[str] = Field(default=None, max_length=1024, nullable=True,
                                      description="Link to PDF or official document")
    version:    Optional[str] = Field(default=None, max_length=50, nullable=True)
    language:   str           = Field(default="en", max_length=10, nullable=False,
                                      description="BCP 47 language tag e.g. 'en', 'sw'")

    is_active: bool = Field(default=True, nullable=False)
    is_public: bool = Field(default=True, nullable=False,
                            description="Publicly visible without authentication")

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
    )


# ── PlatformGuide ─────────────────────────────────────────────────────────────

class GuideType(str, Enum):
    PROFESSIONAL_GUIDE = "PROFESSIONAL_GUIDE"  # Industry professional guides
    REFERENCE_MANUAL   = "REFERENCE_MANUAL"    # Operational reference manuals
    STANDARD           = "STANDARD"            # Adopted standards
    BEST_PRACTICE      = "BEST_PRACTICE"       # Best practice compilations
    TRAINING_MATERIAL  = "TRAINING_MATERIAL"   # Training / onboarding materials
    CHECKLIST          = "CHECKLIST"           # Process checklists
    TEMPLATE           = "TEMPLATE"            # Document templates
    FAQ                = "FAQ"                 # FAQ guides


class PlatformGuide(SQLModel, table=True):
    """
    Platform-level professional documents, guides, and assistance materials.

    Knowledge base for GRM focal persons, org admins, external auditors,
    and industry professionals.

    industry_id = NULL → general/cross-sector guide
    """
    __tablename__ = "platform_guides"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    industry_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="NULL = general/cross-sector guide",
    )

    title:       str           = Field(max_length=500, nullable=False)
    slug:        str           = Field(max_length=200, nullable=False, unique=True, index=True)
    guide_type:  GuideType     = Field(
        sa_column=Column(SAEnum(GuideType, name="guide_type"), nullable=False, index=True),
    )

    applicable_sectors: Optional[list] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='Industry slugs: ["healthcare", "education", "finance"]',
    )
    target_audience: Optional[str] = Field(
        default=None, max_length=200, nullable=True,
        description="e.g. 'GRM Focal Persons', 'Org Administrators', 'All Staff'",
    )

    content_md:  Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True),
                                       description="Full guide content in Markdown")
    file_url:    Optional[str] = Field(default=None, max_length=1024, nullable=True,
                                       description="Downloadable PDF or document")
    file_format: Optional[str] = Field(default=None, max_length=20, nullable=True,
                                       description="e.g. 'PDF', 'DOCX', 'MD'")

    version:         Optional[str] = Field(default=None, max_length=50,  nullable=True)
    language:        str           = Field(default="en", max_length=10,  nullable=False)
    source_standard: Optional[str] = Field(
        default=None, max_length=300, nullable=True,
        description="e.g. 'ISO 10002:2018', 'IFC PS5', 'UNHCR 2022'",
    )

    is_public: bool = Field(default=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
    )
