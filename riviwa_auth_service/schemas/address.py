# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  schemas/address.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/address.py
═══════════════════════════════════════════════════════════════════════════════
Pydantic schemas for the Address resource.

Three address creation modes
──────────────────────────────
  1. OSM search  — client calls GET /addresses/search to get Nominatim
                   suggestions, picks one, then POSTs with osm_place_id set.
                   The service resolves the full address from Nominatim and
                   stores it.  source = "osm".

  2. GPS / reverse — client sends gps_latitude + gps_longitude.
                   The service calls Nominatim /reverse, fills structured
                   fields, and stores.  source = "gps".

  3. Manual       — client sends all fields directly with no OSM data.
                   source = "manual".  line1 is recommended but not required
                   (community-level addresses may only have ward/mtaa + GPS).

Response
──────────────────────────────
  AddressResponse includes both the structured fields AND the OSM metadata
  so the frontend can render a map pin (lat/lon) and a Nominatim permalink.

Nominatim search result
──────────────────────────────
  NominatimResult — lightweight DTO returned by GET /addresses/search.
  The frontend renders these as autocomplete suggestions.  The client then
  chooses one and includes its place_id in AddressCreateRequest so the
  service can auto-populate all fields without a second round-trip.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Nominatim search / reverse result DTO
# ─────────────────────────────────────────────────────────────────────────────

class NominatimResult(BaseModel):
    """
    One result row from Nominatim /search or /reverse.
    Returned by GET /addresses/search and GET /addresses/reverse.
    The client shows these as suggestions; the selected result is later
    submitted as part of AddressCreateRequest.
    """
    place_id:      int
    osm_id:        Optional[int]   = None
    osm_type:      Optional[str]   = None
    display_name:  str
    place_rank:    Optional[int]   = None
    place_type:    Optional[str]   = None
    address_class: Optional[str]   = None
    # Structured address components (from Nominatim addressdetails=1)
    line1:         Optional[str]   = None   # road + house_number
    city:          Optional[str]   = None
    postal_code:   Optional[str]   = None
    country_code:  Optional[str]   = None
    region:        Optional[str]   = None   # state
    district:      Optional[str]   = None   # state_district / county
    lga:           Optional[str]   = None   # county
    ward:          Optional[str]   = None   # suburb / city_district
    mtaa:          Optional[str]   = None   # quarter / neighbourhood
    # GPS
    gps_latitude:  Optional[float] = None
    gps_longitude: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────────────────────

class AddressCreateRequest(BaseModel):
    """
    Body for POST /addresses.

    GPS coordinates are always the precise ground truth.
    When gps_latitude + gps_longitude are provided they are stored exactly
    as sent — Nominatim's own coordinates are NEVER used in their place.

    Creation modes:
      · osm_place_id + GPS   → OSM text fields from Nominatim, exact GPS stored.
      · osm_place_id only    → All fields (text + coords) from Nominatim.
      · GPS only             → Reverse-geocode for text fields, exact GPS stored.
      · neither              → Manual: store exactly what the client sends.

    In all modes the client must also supply entity_type, entity_id, and
    address_type to attach the address to an entity.
    """
    # ── Entity binding ────────────────────────────────────────────────────────
    entity_type: str = Field(
        default="user",
        description="'user' | 'org_subproject' | 'stakeholder'",
    )
    entity_id: uuid.UUID = Field(
        description="UUID of the entity this address belongs to.",
    )
    address_type: str = Field(
        default="home",
        description=(
            "User: 'billing'|'shipping'|'home'. "
            "OrgSubProject: 'site'|'office'|'depot'. "
            "Stakeholder: 'registered'|'operational'|'contact'."
        ),
    )
    label: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Human label e.g. 'Main site', 'Registered HQ'.",
    )
    is_default: bool = False

    # ── Mode 1: OSM place_id (from search result) ─────────────────────────────
    osm_place_id: Optional[int] = Field(
        default=None,
        description=(
            "Nominatim place_id from a previous /addresses/search call. "
            "When set, address text fields (display_name, ward, region, etc.) "
            "are populated from Nominatim. If gps_latitude + gps_longitude are "
            "also provided, those GPS coordinates are stored as-is — Nominatim's "
            "own coordinates are ignored."
        ),
    )
    # Echo these from the NominatimResult you received from /search — avoids
    # a second server-side Nominatim round-trip.
    display_name: Optional[str] = Field(
        default=None,
        description="Full display string echoed from the NominatimResult (osm mode).",
    )
    osm_id:   Optional[int] = Field(default=None, description="OSM element ID from NominatimResult.")
    osm_type: Optional[str] = Field(default=None, max_length=10, description="'node'|'way'|'relation' from NominatimResult.")

    # ── Mode 2: GPS coordinates (reverse geocode) ─────────────────────────────
    gps_latitude:  Optional[float] = Field(
        default=None,
        ge=-90.0, le=90.0,
        description="Decimal degrees latitude. Required for GPS mode.",
    )
    gps_longitude: Optional[float] = Field(
        default=None,
        ge=-180.0, le=180.0,
        description="Decimal degrees longitude. Required for GPS mode.",
    )

    # ── Mode 3: Manual fields ─────────────────────────────────────────────────
    line1:        Optional[str] = Field(default=None, max_length=200)
    line2:        Optional[str] = Field(default=None, max_length=200)
    city:         Optional[str] = Field(default=None, max_length=100)
    state:        Optional[str] = Field(default=None, max_length=100)
    postal_code:  Optional[str] = Field(default=None, max_length=20)
    country_code: str           = Field(default="TZ", max_length=2)
    region:       Optional[str] = Field(default=None, max_length=150)
    district:     Optional[str] = Field(default=None, max_length=100)
    lga:          Optional[str] = Field(default=None, max_length=100)
    ward:         Optional[str] = Field(default=None, max_length=100)
    mtaa:         Optional[str] = Field(default=None, max_length=100)
    address_notes: Optional[str] = Field(default=None)

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        allowed = {"user", "org_subproject", "stakeholder"}
        if v not in allowed:
            raise ValueError(f"entity_type must be one of {allowed}")
        return v

    @field_validator("address_type")
    @classmethod
    def validate_address_type(cls, v: str) -> str:
        allowed = {
            "billing", "shipping", "home",       # user
            "site", "office", "depot",            # org_subproject
            "registered", "operational", "contact",  # stakeholder
        }
        if v not in allowed:
            raise ValueError(f"address_type must be one of {allowed}")
        return v

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def check_gps_pair(self) -> "AddressCreateRequest":
        lat, lon = self.gps_latitude, self.gps_longitude
        if (lat is None) != (lon is None):
            raise ValueError(
                "gps_latitude and gps_longitude must both be provided or both omitted."
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────────────────────────────────────

class AddressUpdateRequest(BaseModel):
    """Body for PATCH /addresses/{address_id}. All fields optional."""
    address_type:  Optional[str]  = None
    label:         Optional[str]  = Field(default=None, max_length=100)
    is_default:    Optional[bool] = None
    line1:         Optional[str]  = Field(default=None, max_length=200)
    line2:         Optional[str]  = Field(default=None, max_length=200)
    city:          Optional[str]  = Field(default=None, max_length=100)
    state:         Optional[str]  = Field(default=None, max_length=100)
    postal_code:   Optional[str]  = Field(default=None, max_length=20)
    country_code:  Optional[str]  = Field(default=None, max_length=2)
    region:        Optional[str]  = Field(default=None, max_length=150)
    district:      Optional[str]  = Field(default=None, max_length=100)
    lga:           Optional[str]  = Field(default=None, max_length=100)
    ward:          Optional[str]  = Field(default=None, max_length=100)
    mtaa:          Optional[str]  = Field(default=None, max_length=100)
    gps_latitude:  Optional[float] = Field(default=None, ge=-90.0,   le=90.0)
    gps_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    address_notes: Optional[str]  = None

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v

    @field_validator("address_type")
    @classmethod
    def validate_address_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {
            "billing", "shipping", "home",
            "site", "office", "depot",
            "registered", "operational", "contact",
        }
        if v not in allowed:
            raise ValueError(f"address_type must be one of {allowed}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────────────────────

class AddressResponse(BaseModel):
    """Full address record returned by all write endpoints and GET single."""
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    entity_type:   str
    entity_id:     uuid.UUID
    address_type:  str
    label:         Optional[str]   = None
    is_default:    bool

    # Source & OSM metadata
    source:        str
    osm_id:        Optional[int]   = None
    osm_type:      Optional[str]   = None
    place_id:      Optional[int]   = None
    display_name:  Optional[str]   = None
    place_rank:    Optional[int]   = None
    place_type:    Optional[str]   = None
    address_class: Optional[str]   = None

    # Structured address
    line1:         Optional[str]   = None
    line2:         Optional[str]   = None
    city:          Optional[str]   = None
    state:         Optional[str]   = None
    postal_code:   Optional[str]   = None
    country_code:  str

    # Tanzania hierarchy
    region:        Optional[str]   = None
    district:      Optional[str]   = None
    lga:           Optional[str]   = None
    ward:          Optional[str]   = None
    mtaa:          Optional[str]   = None

    # GPS
    gps_latitude:  Optional[float] = None
    gps_longitude: Optional[float] = None

    address_notes: Optional[str]   = None

    # Computed display helper
    display_lines: Optional[List[str]] = None

    created_at:    datetime
    updated_at:    datetime


class AddressListResponse(BaseModel):
    """Paginated list of addresses for an entity."""
    total:     int
    addresses: List[AddressResponse]
