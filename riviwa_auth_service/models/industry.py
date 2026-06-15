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
