"""
models/address.py
═══════════════════════════════════════════════════════════════════════════════
Shared reusable Address model for any entity in the platform.

DESIGN EVOLUTION
──────────────────────────────────────────────────────────────────────────────
Originally tied exclusively to User (billing / shipping / home). Extended to
be entity-agnostic so it can be referenced by:

  User          → personal addresses (billing, shipping, home)
  OrgSubProject → physical site address of a work package
  Stakeholder   → where the stakeholder entity is located
                  (cross-service soft link from stakeholder_service)

ENTITY PATTERN
──────────────────────────────────────────────────────────────────────────────
  entity_type   identifies which table the address belongs to:
                  "user" | "org_subproject" | "stakeholder"

  entity_id     the UUID of the owning row in that table.
                  For User:          the user.id (also stored in user_id FK)
                  For OrgSubProject: the org_sub_project.id (also in subproject_id FK)
                  For Stakeholder:   the stakeholder.id from stakeholder_service
                                     (soft link — no FK constraint across services)

  user_id       kept as a nullable FK for backward compatibility and for fast
                JOIN queries when entity_type = "user".

  subproject_id nullable FK to org_sub_projects. Populated when
                entity_type = "org_subproject". Enables ON DELETE CASCADE.

ADDRESS FIELD MAPPING (Tanzania administrative hierarchy)
──────────────────────────────────────────────────────────────────────────────
  The existing Western fields are kept for global compatibility.
  Tanzania-specific fields are added alongside them:

  Western / global          Tanzania equivalent
  ──────────────────────    ────────────────────────────────────────
  country_code "TZ"         country_code "TZ"
  state                     region    e.g. "Dar es Salaam", "Coast"
  city                      district  e.g. "Ilala", "Kinondoni"   (city can also be used)
  —                         lga       e.g. "Ilala Municipal Council"
  —                         ward      e.g. "Jangwani", "Msimbazi"
  —                         mtaa      e.g. "Mtaa wa Gerezani"    (sub-ward / cell)
  line1                     street_address / line1  (Plot no. + street)
  line2                     additional detail
  postal_code               postal_code  (rare in Tanzania but used by formal entities)

  GPS coordinates:
    latitude / longitude — replaces OrgLocation's separate field names,
    unified as gps_latitude / gps_longitude.

  address_notes — directions, landmarks, access instructions.
    Especially important for community groups and field addresses
    that don't have a formal postal address.

BACKWARD COMPATIBILITY
──────────────────────────────────────────────────────────────────────────────
  All existing User address rows continue to work unchanged:
    · user_id remains a FK (now nullable, but populated for User addresses)
    · address_type = "billing" | "shipping" | "home" is preserved
    · line1, line2, city, state, postal_code, country_code are unchanged
    · is_default is preserved

  The only breaking change: user_id column is now nullable at the DB level.
  Existing rows are unaffected (their user_id is already set).

CROSS-SERVICE USAGE (stakeholder_service)
──────────────────────────────────────────────────────────────────────────────
  stakeholder_service stores Stakeholder.address_id as a UUID soft link
  to this table. There is NO FK constraint across service boundaries.
  Integrity is maintained by:
    · The stakeholder_service API creating an Address via auth_service's
      /api/v1/addresses endpoint before setting the soft link.
    · Kafka events: when an Address is deleted (entity_type=stakeholder),
      auth_service publishes address.deleted on riviwa.org.events and
      stakeholder_service nulls out Stakeholder.address_id.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User
    from models.org_project import OrgSubProject


class Address(SQLModel, table=True):
    """
    Reusable address record for any platform entity.

    address_type values:
      User addresses:          "billing" | "shipping" | "home"
      OrgSubProject addresses: "site" | "office" | "depot"
      Stakeholder addresses:   "registered" | "operational" | "contact"
    """
    __tablename__ = "addresses"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── Entity ownership (polymorphic) ────────────────────────────────────────
    entity_type: str = Field(
        max_length=50,
        nullable=False,
        index=True,
        default="user",
        description=(
            "Which entity owns this address. "
            "'user' | 'org_subproject' | 'stakeholder'"
        ),
    )
    entity_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        description="UUID of the owning row in the entity_type table.",
    )

    # ── Convenience FKs for same-DB entities (nullable for cross-service) ─────
    # user_id: populated when entity_type = "user". Enables cascading deletes
    # and efficient User → addresses JOINs without going through entity_id.
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        description=(
            "FK to users.id. Set when entity_type='user'. "
            "Null for org_subproject and stakeholder addresses."
        ),
    )
    # subproject_id: populated when entity_type = "org_subproject".
    subproject_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_sub_projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        description=(
            "FK to org_sub_projects.id. Set when entity_type='org_subproject'. "
            "Null for user and stakeholder addresses."
        ),
    )

    # ── Address classification ─────────────────────────────────────────────────
    address_type: str = Field(
        default="home",
        max_length=30,
        nullable=False,
        description=(
            "User:         'billing' | 'shipping' | 'home'\n"
            "OrgSubProject: 'site' | 'office' | 'depot'\n"
            "Stakeholder:   'registered' | 'operational' | 'contact'"
        ),
    )
    label: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Human label e.g. 'Main site', 'Contractor yard', 'Registered HQ'.",
    )
    is_default: bool = Field(
        default=False,
        nullable=False,
        description="True for the primary address when an entity has multiple.",
    )

    # ── Standard address fields (global / Western format) ─────────────────────
    # Retained for backward compatibility and international addresses.
    line1:       str            = Field(max_length=200, nullable=False,
                                        description="Street address line 1 e.g. 'Plot 14, Lindi Street'.")
    line2:       Optional[str]  = Field(default=None, max_length=200, nullable=True,
                                        description="Additional detail e.g. 'Floor 3, Suite 301'.")
    city:        Optional[str]  = Field(default=None, max_length=100, nullable=True,
                                        description="City or town. For Tanzania, often the LGA or district name.")
    state:       Optional[str]  = Field(default=None, max_length=100, nullable=True,
                                        description="State or province. For Tanzania, use the 'region' field instead.")
    postal_code: Optional[str]  = Field(default=None, max_length=20,  nullable=True)
    country_code: str           = Field(max_length=2, nullable=False, default="TZ",
                                        description="ISO 3166-1 alpha-2 e.g. 'TZ', 'KE', 'UG', 'US'.")

    # ── Tanzania administrative hierarchy fields ───────────────────────────────
    # Use these for Tanzanian addresses alongside or instead of city/state.
    # Hierarchy: country → region → district → lga → ward → mtaa
    region:   Optional[str] = Field(
        default=None, max_length=150, nullable=True, index=True,
        description="Administrative region e.g. 'Dar es Salaam', 'Coast', 'Morogoro'.",
    )
    district: Optional[str] = Field(
        default=None, max_length=100, nullable=True, index=True,
        description="District e.g. 'Ilala', 'Kinondoni', 'Temeke', 'Ubungo', 'Kisarawe'.",
    )
    lga: Optional[str] = Field(
        default=None, max_length=100, nullable=True, index=True,
        description="Local Government Authority e.g. 'Ilala Municipal Council'.",
    )
    ward: Optional[str] = Field(
        default=None, max_length=100, nullable=True, index=True,
        description="Ward name e.g. 'Jangwani', 'Kariakoo', 'Msimbazi'.",
    )
    mtaa: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Sub-ward / cell (Mtaa) e.g. 'Mtaa wa Gerezani'.",
    )

    # ── GPS coordinates ────────────────────────────────────────────────────────
    gps_latitude:  Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees latitude. Positive = North, negative = South.",
    )
    gps_longitude: Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees longitude.",
    )

    # ── Access notes ──────────────────────────────────────────────────────────
    address_notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Directions, landmarks, or access instructions. "
            "e.g. 'Near Jangwani market, second building after the mosque'. "
            "e.g. 'Access via Morogoro Road, site entrance 200m past Jangwani Bridge'."
        ),
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
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
    user: User = Relationship(
        back_populates="addresses",
        sa_relationship_kwargs={"foreign_keys": "[Address.user_id]"},
    )
    subproject: OrgSubProject = Relationship(
        back_populates="addresses",
        sa_relationship_kwargs={"foreign_keys": "[Address.subproject_id]"},
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def full_address_lines(self) -> list[str]:
        """
        Returns ordered non-empty address components as display lines.
        Uses Tanzania hierarchy when available, falls back to Western fields.
        """
        parts = []
        if self.line1:              parts.append(self.line1)
        if self.line2:              parts.append(self.line2)
        if self.mtaa:               parts.append(self.mtaa)
        if self.ward:               parts.append(f"Ward: {self.ward}")
        if self.lga or self.city:   parts.append(self.lga or self.city)
        if self.district:           parts.append(self.district)
        if self.region or self.state: parts.append(self.region or self.state)
        if self.postal_code:        parts.append(self.postal_code)
        if self.country_code:       parts.append(self.country_code)
        return parts

    def to_dict(self) -> dict:
        """Serialise all address fields as a flat dict for API responses."""
        return {
            "id":             str(self.id),
            "entity_type":    self.entity_type,
            "address_type":   self.address_type,
            "label":          self.label,
            "is_default":     self.is_default,
            "line1":          self.line1,
            "line2":          self.line2,
            "city":           self.city,
            "state":          self.state,
            "postal_code":    self.postal_code,
            "country_code":   self.country_code,
            "region":         self.region,
            "district":       self.district,
            "lga":            self.lga,
            "ward":           self.ward,
            "mtaa":           self.mtaa,
            "gps_latitude":   self.gps_latitude,
            "gps_longitude":  self.gps_longitude,
            "address_notes":  self.address_notes,
            "created_at":     self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        loc = self.lga or self.city or self.district or "?"
        return (
            f"<Address [{self.address_type}] "
            f"{self.line1!r}, {loc} "
            f"entity={self.entity_type}:{self.entity_id}>"
        )
