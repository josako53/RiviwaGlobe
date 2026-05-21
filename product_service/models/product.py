"""
models/product.py — Core product listing models for the Riviwa marketplace.

Inspired by Amazon's two-layer product data model:
  - Product type  → internal schema (determines required attributes & validation rules)
  - Browse node   → customer-facing category hierarchy (determines where it appears)

RSIN (Riviwa Standard Identification Number) replaces Amazon's ASIN.
Format: R + 9 uppercase alphanumeric chars  e.g. R09XJ3KLMN
Auto-generated on first publish; immutable thereafter.

Product type is also immutable after first publish — reclassification requires
deleting and recreating the listing with the same GTIN/industry_unique_id.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, Numeric, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class ProductType(str, Enum):
    """
    Internal schema blueprint — determines which category-specific attribute
    table applies and which fields are required before a listing goes BUYABLE.
    Immutable after first publish.
    """
    # ── Electronics — Computers ──────────────────────────────────────────────
    LAPTOP              = "LAPTOP"
    DESKTOP             = "DESKTOP"
    TABLET              = "TABLET"
    MONITOR             = "MONITOR"
    COMPUTER_COMPONENT  = "COMPUTER_COMPONENT"
    NETWORKING_DEVICE   = "NETWORKING_DEVICE"

    # ── Electronics — Consumer ───────────────────────────────────────────────
    SMARTPHONE          = "SMARTPHONE"
    CAMERA              = "CAMERA"
    HEADPHONE           = "HEADPHONE"
    SPEAKER             = "SPEAKER"
    TV                  = "TV"
    HOME_THEATER        = "HOME_THEATER"
    WEARABLE            = "WEARABLE"

    # ── Apparel ──────────────────────────────────────────────────────────────
    SHIRT               = "SHIRT"
    PANTS               = "PANTS"
    DRESS               = "DRESS"
    JACKET              = "JACKET"
    UNDERWEAR           = "UNDERWEAR"
    ACTIVEWEAR          = "ACTIVEWEAR"
    SUIT                = "SUIT"
    TRADITIONAL_WEAR    = "TRADITIONAL_WEAR"

    # ── Footwear ─────────────────────────────────────────────────────────────
    SHOES               = "SHOES"
    SANDALS             = "SANDALS"
    BOOTS               = "BOOTS"
    SNEAKERS            = "SNEAKERS"

    # ── Home & Kitchen ───────────────────────────────────────────────────────
    DRINKING_CUP        = "DRINKING_CUP"
    COOKWARE            = "COOKWARE"
    SMALL_APPLIANCE     = "SMALL_APPLIANCE"
    LARGE_APPLIANCE     = "LARGE_APPLIANCE"
    FURNITURE           = "FURNITURE"
    HOME_DECOR          = "HOME_DECOR"
    STORAGE             = "STORAGE"
    CLEANING_SUPPLY     = "CLEANING_SUPPLY"

    # ── Home — Bedding & Bath ────────────────────────────────────────────────
    PILLOW              = "PILLOW"
    BEDDING             = "BEDDING"
    TOWEL               = "TOWEL"
    MATTRESS            = "MATTRESS"

    # ── Health & Personal Care ───────────────────────────────────────────────
    SUPPLEMENT          = "SUPPLEMENT"
    MEDICATION          = "MEDICATION"
    PERSONAL_CARE       = "PERSONAL_CARE"
    MEDICAL_DEVICE      = "MEDICAL_DEVICE"

    # ── Food & Beverage ──────────────────────────────────────────────────────
    FOOD_AND_BEVERAGE   = "FOOD_AND_BEVERAGE"
    GROCERY             = "GROCERY"
    ORGANIC_PRODUCT     = "ORGANIC_PRODUCT"
    FROZEN_FOOD         = "FROZEN_FOOD"
    CHILLED_FOOD        = "CHILLED_FOOD"
    BEVERAGE            = "BEVERAGE"
    SNACK               = "SNACK"
    CONDIMENT           = "CONDIMENT"

    # ── Toys & Games ─────────────────────────────────────────────────────────
    TOY                 = "TOY"
    BOARD_GAME          = "BOARD_GAME"
    PUZZLE              = "PUZZLE"
    OUTDOOR_TOY         = "OUTDOOR_TOY"
    VIDEO_GAME          = "VIDEO_GAME"

    # ── Books & Media ────────────────────────────────────────────────────────
    BOOK                = "BOOK"
    MUSIC               = "MUSIC"
    MOVIE               = "MOVIE"
    DIGITAL_CONTENT     = "DIGITAL_CONTENT"

    # ── Automotive — Vehicles (cars) ─────────────────────────────────────────
    CAR_NEW             = "CAR_NEW"
    CAR_USED            = "CAR_USED"
    CAR_CERTIFIED       = "CAR_CERTIFIED"       # Certified Pre-Owned
    SUV_NEW             = "SUV_NEW"
    SUV_USED            = "SUV_USED"
    TRUCK_NEW           = "TRUCK_NEW"
    TRUCK_USED          = "TRUCK_USED"
    VAN_NEW             = "VAN_NEW"
    VAN_USED            = "VAN_USED"
    ELECTRIC_VEHICLE    = "ELECTRIC_VEHICLE"
    HYBRID_VEHICLE      = "HYBRID_VEHICLE"
    MOTORCYCLE          = "MOTORCYCLE"
    BUS                 = "BUS"
    MINIBUS             = "MINIBUS"

    # ── Automotive — Parts & Accessories ─────────────────────────────────────
    AUTO_PART           = "AUTO_PART"
    AUTO_ACCESSORY      = "AUTO_ACCESSORY"
    TIRE                = "TIRE"

    # ── Other ────────────────────────────────────────────────────────────────
    TOOL                = "TOOL"
    SPORTS_EQUIPMENT    = "SPORTS_EQUIPMENT"
    PET_SUPPLY          = "PET_SUPPLY"
    OFFICE_SUPPLY       = "OFFICE_SUPPLY"
    JEWELRY             = "JEWELRY"
    WATCH               = "WATCH"
    BABY_PRODUCT        = "BABY_PRODUCT"
    AGRICULTURAL        = "AGRICULTURAL"
    INDUSTRIAL          = "INDUSTRIAL"

    # ── Services ─────────────────────────────────────────────────────────────
    SERVICE             = "SERVICE"             # Generic service offering
    CONSULTING_SERVICE  = "CONSULTING_SERVICE"  # Advisory / professional services
    DIGITAL_SERVICE     = "DIGITAL_SERVICE"     # SaaS, APIs, digital subscriptions
    MAINTENANCE_SERVICE = "MAINTENANCE_SERVICE" # Repairs, upkeep, AMC contracts
    INSTALLATION_SERVICE= "INSTALLATION_SERVICE"# Setup, deployment, commissioning
    TRAINING_SERVICE    = "TRAINING_SERVICE"    # Workshops, courses, certifications
    HEALTHCARE_SERVICE  = "HEALTHCARE_SERVICE"  # Medical, wellness, lab services
    LOGISTICS_SERVICE   = "LOGISTICS_SERVICE"   # Freight, delivery, warehousing


class ListingStatus(str, Enum):
    DRAFT           = "DRAFT"           # Not yet submitted
    PENDING_REVIEW  = "PENDING_REVIEW"  # Submitted, awaiting moderation
    BUYABLE         = "BUYABLE"         # Live and purchasable
    DISCOVERABLE    = "DISCOVERABLE"    # Visible but not purchasable
    SUPPRESSED      = "SUPPRESSED"      # Hidden by platform due to policy/data issue
    INCOMPLETE      = "INCOMPLETE"      # Missing required attributes
    INACTIVE        = "INACTIVE"        # Manually deactivated by seller
    REJECTED        = "REJECTED"        # Failed moderation


class FulfillmentMethod(str, Enum):
    MERCHANT    = "MERCHANT"    # Seller ships directly
    RIVIWA      = "RIVIWA"      # Riviwa fulfillment centre (like FBA)
    PICKUP      = "PICKUP"      # In-store / local pickup only
    DIGITAL     = "DIGITAL"     # Digital delivery (download/stream)


class ProductCondition(str, Enum):
    NEW             = "NEW"
    USED_LIKE_NEW   = "USED_LIKE_NEW"
    USED_GOOD       = "USED_GOOD"
    USED_ACCEPTABLE = "USED_ACCEPTABLE"
    REFURBISHED     = "REFURBISHED"
    OPEN_BOX        = "OPEN_BOX"
    PARTS_ONLY      = "PARTS_ONLY"


class VariationTheme(str, Enum):
    """
    Defines which axes create child variants under a parent RSIN.
    E.g. a shirt parent groups Red/S, Red/M, Blue/S, Blue/M children.
    """
    COLOR           = "COLOR"
    SIZE            = "SIZE"
    COLOR_SIZE      = "COLOR_SIZE"
    FLAVOR          = "FLAVOR"
    SIZE_FLAVOR     = "SIZE_FLAVOR"
    STYLE           = "STYLE"
    PACK_SIZE       = "PACK_SIZE"
    SCENT           = "SCENT"
    MATERIAL        = "MATERIAL"
    CONFIGURATION   = "CONFIGURATION"
    TRIM            = "TRIM"            # Vehicles: base / sport / premium
    COLOR_TRIM      = "COLOR_TRIM"      # Vehicles: color + trim combined


class ImageRole(str, Enum):
    MAIN            = "MAIN"
    ALTERNATE       = "ALTERNATE"
    SWATCH          = "SWATCH"          # Color/material close-up
    INGREDIENTS     = "INGREDIENTS"     # Required for food
    NUTRITION_FACTS = "NUTRITION_FACTS" # Required for food
    DIMENSIONS      = "DIMENSIONS"
    LIFESTYLE       = "LIFESTYLE"
    CERTIFICATE     = "CERTIFICATE"     # Compliance / certification scan


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_RSIN_CHARS = string.ascii_uppercase + string.digits


def generate_rsin() -> str:
    """Generate a Riviwa Standard Identification Number: R + 9 random chars."""
    suffix = "".join(secrets.choice(_RSIN_CHARS) for _ in range(9))
    return f"R{suffix}"


# ══════════════════════════════════════════════════════════════════════════════
# ORG CACHE
# Local cache of organisation records populated by consuming
# riviwa.organisation.events from auth_service Kafka topic.
# Prevents cross-service HTTP calls for org validation.
# ══════════════════════════════════════════════════════════════════════════════

class OrgCache(SQLModel, table=True):
    __tablename__ = "org_cache"

    org_id: UUID = Field(primary_key=True)
    name: str = Field(max_length=300)
    slug: Optional[str] = Field(default=None, max_length=200)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    synced_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# CORE PRODUCT TABLE
# ══════════════════════════════════════════════════════════════════════════════

class Product(SQLModel, table=True):
    """
    Master product record. One row per sellable unit (or parent of a variant family).

    Classification fields (product_type, browse_node_id, item_type_keyword) are
    immutable after the listing is first published — changing them requires
    deleting and recreating the product with the same GTIN / industry_unique_id.
    """
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organisation_id", "seller_sku", name="uq_org_sku"),
    )

    # ── Primary Key ─────────────────────────────────────────────────────────
    product_id: UUID = Field(default_factory=uuid4, primary_key=True)

    # ── Riviwa Catalogue Identifier ──────────────────────────────────────────
    # Auto-assigned on first publish. Shared across all sellers offering the
    # same physical product. Immutable once set.
    rsin: Optional[str] = Field(
        default=None,
        max_length=10,
        unique=True,
        index=True,
        description="Riviwa Standard Identification Number (R + 9 chars). Auto-generated on publish.",
    )

    # ── Seller's Private Inventory Code ─────────────────────────────────────
    seller_sku: str = Field(max_length=100, index=True)

    # ── Global Trade Identifiers ─────────────────────────────────────────────
    # At least one GTIN is required to create a new RSIN (links product to
    # global catalogue; corresponds to the barcode on physical packaging).
    upc: Optional[str] = Field(default=None, max_length=20, description="Universal Product Code")
    ean: Optional[str] = Field(default=None, max_length=20, description="European Article Number")
    gtin: Optional[str] = Field(default=None, max_length=20, description="Global Trade Item Number")
    isbn: Optional[str] = Field(default=None, max_length=20, description="Books only")
    mpn: Optional[str] = Field(default=None, max_length=100, description="Manufacturer Part Number")

    # ── Industry-Specific Unique Identifier ──────────────────────────────────
    # Category-specific alternative to GTIN:
    #   Cars       → VIN  (Vehicle Identification Number, 17 chars)
    #   Phones     → IMEI (15 digits)
    #   Pharma     → NDC  (National Drug Code)
    #   Electronics→ Serial number / IMEI
    #   Machinery  → Equipment serial number
    industry_unique_id: Optional[str] = Field(
        default=None,
        max_length=100,
        index=True,
        description="VIN (cars), IMEI (phones), NDC (pharma), serial no., etc.",
    )
    industry_id_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Label for industry_unique_id e.g. VIN, IMEI, NDC, SERIAL",
    )

    # ── Classification (IMMUTABLE after publish) ─────────────────────────────
    # sa_column=Column(String) prevents asyncpg from trying to cast to a
    # non-existent PostgreSQL enum type (the DB column is VARCHAR).
    product_type: str = Field(sa_column=Column(String(50), nullable=False, index=True))
    # Customer-facing category tree leaf node, e.g. "Electronics > Computers > Laptops"
    browse_node_id: Optional[str] = Field(default=None, max_length=50)
    browse_node_path: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Full human-readable path e.g. 'Automotive > Cars > Sedans'",
    )
    # Most critical backend search/browse placement field
    item_type_keyword: Optional[str] = Field(default=None, max_length=200)

    # ── Ownership ────────────────────────────────────────────────────────────
    organisation_id: UUID = Field(index=True)
    # Person or team accountable for this listing's accuracy and compliance
    product_supervisor: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Name, user ID, or role of the person responsible for this listing",
    )

    # ── Core Listing Content ─────────────────────────────────────────────────
    title: str = Field(max_length=500)
    brand: str = Field(max_length=200)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model_number: Optional[str] = Field(default=None, max_length=100)

    # ── Description ──────────────────────────────────────────────────────────
    # Bullet points (up to 5, max 500 chars each) → stored in ProductBulletPoint
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Up to 2,000 chars. Focus on unique properties and features.",
    )

    # ── Usage ─────────────────────────────────────────────────────────────────
    usage: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Intended use, target application, or use-case context.",
    )
    how_to_use: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description=(
            "Step-by-step instructions on how to use, install, or operate the product or service. "
            "Supports Markdown formatting. Shown on the product detail page as a collapsible section."
        ),
    )

    # ── Production & Origin ──────────────────────────────────────────────────
    production_location: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Country, city, or facility where the product was manufactured.",
    )
    country_of_origin: Optional[str] = Field(
        default=None, max_length=100,
        description="ISO 2-letter country code or full country name, e.g. 'TZ' or 'Tanzania'.",
    )
    made_in: Optional[str] = Field(
        default=None, max_length=150,
        description="Display label shown on the product listing, e.g. 'Made in Tanzania' or 'Assembled in Kenya'.",
    )

    # ── Offer Details ────────────────────────────────────────────────────────
    price: Decimal = Field(sa_column=Column(Numeric(14, 2)))
    currency: str = Field(default="TZS", max_length=3)
    condition: str = Field(default="NEW", sa_column=Column(String(30), nullable=False))
    quantity: int = Field(default=0, ge=0)
    fulfillment_method: str = Field(default="MERCHANT", sa_column=Column(String(20), nullable=False))
    # FBA-equivalent shelf life (days). Required for consumables sent to Riviwa centres.
    fulfillment_center_shelf_life_days: Optional[int] = Field(default=None, ge=0, le=1825)

    # ── Physical Dimensions ──────────────────────────────────────────────────
    item_weight: Optional[float] = Field(default=None, description="Weight in item_weight_unit")
    item_weight_unit: str = Field(default="kg", max_length=10)
    length: Optional[float] = Field(default=None)
    width: Optional[float] = Field(default=None)
    height: Optional[float] = Field(default=None)
    dimensions_unit: str = Field(default="cm", max_length=10)

    # ── Main Image ───────────────────────────────────────────────────────────
    # Additional images stored in ProductImage table.
    main_image_url: Optional[str] = Field(default=None, max_length=1000)

    # ── Variation / Parent–Child ─────────────────────────────────────────────
    # Parent RSIN is non-buyable; groups a family of variants (e.g. all shirt sizes).
    # Children share the parent's product_type and browse classification.
    is_parent: bool = Field(default=False)
    parent_product_id: Optional[UUID] = Field(default=None, index=True)
    variation_theme: Optional[str] = Field(default=None, sa_column=Column(String(30), nullable=True))
    # e.g. {"color": "Red", "size": "L"} for a child variant
    variation_values: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # ── Listing Status & Flags ───────────────────────────────────────────────
    listing_status: str = Field(default="DRAFT", sa_column=Column(String(20), nullable=False, index=True))
    is_active: bool = Field(default=True, index=True)
    is_gated: bool = Field(default=False, description="Requires platform approval before selling")
    suppression_reason: Optional[str] = Field(default=None, max_length=500)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = Field(default=None)


# ══════════════════════════════════════════════════════════════════════════════
# BULLET POINTS
# Up to 5 per product, max 500 chars each. Used in the "key product features"
# section of the listing. Displayed as a bulleted list on the product page.
# ══════════════════════════════════════════════════════════════════════════════

class ProductBulletPoint(SQLModel, table=True):
    __tablename__ = "product_bullet_points"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(index=True, foreign_key="products.product_id")
    position: int = Field(ge=1, le=5, description="Display order (1–5)")
    content: str = Field(max_length=500)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT IMAGES
# main_image_url lives on Product; all additional images live here.
# Food listings must include INGREDIENTS and NUTRITION_FACTS images.
# ══════════════════════════════════════════════════════════════════════════════

class ProductImage(SQLModel, table=True):
    __tablename__ = "product_images"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(index=True, foreign_key="products.product_id")
    role: str = Field(default="ALTERNATE", sa_column=Column(String(30), nullable=False))
    position: int = Field(default=1, ge=1, description="Display order among same role")
    url: str = Field(max_length=1000)
    alt_text: Optional[str] = Field(default=None, max_length=200)


# ══════════════════════════════════════════════════════════════════════════════
# FLEXIBLE NAME–VALUE ATTRIBUTES
# Generic key-value store for any attribute not covered by the typed tables.
# Also used for custom / industry-specific fields.
#
# Examples:
#   product_name="Engine Displacement" → value="2.0L"
#   product_name="Warranty Period"     → value="2 years"
#   product_name="Certification"       → value="ISO 9001"
#   product_name="Charging Standard"   → value="USB-C PD 65W"
# ══════════════════════════════════════════════════════════════════════════════

class ProductAttribute(SQLModel, table=True):
    __tablename__ = "product_attributes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(index=True, foreign_key="products.product_id")
    # Human-readable label shown on the listing detail page
    attribute_name: str = Field(max_length=200, description="e.g. 'Engine Displacement', 'Certification'")
    attribute_value: str = Field(max_length=1000, description="e.g. '2.0L', 'ISO 9001'")
    # Optional unit e.g. "L", "years", "kg", "km/h"
    unit: Optional[str] = Field(default=None, max_length=50)
    # Groups attributes into sections on the detail page (optional UX hint)
    group: Optional[str] = Field(default=None, max_length=100, description="e.g. 'Engine', 'Safety', 'Dimensions'")
    position: int = Field(default=0, description="Display order within group")
    is_searchable: bool = Field(default=False, description="Index this value for search filtering")
    # Optional link to an org custom field definition (null = ad-hoc attribute)
    custom_field_def_id: Optional[UUID] = Field(
        default=None, nullable=True, index=True,
        description="FK to org_product_custom_field_defs.id — links to org-defined field template",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ORG CUSTOM FIELD DEFINITIONS
# Each organisation can define their own required / optional product attributes.
# These become templates that appear in the product edit form for that org.
#
# Examples:
#   - Hospital org might add: "Batch Number", "Expiry Date", "License Number"
#   - Food org might add: "Nutritional Grade", "Halal Certified"
#   - Pharma org might add: "NDC Code", "Controlled Substance Level"
#   - Manufacturer might add: "Warranty Terms", "Compliance Standards"
# ══════════════════════════════════════════════════════════════════════════════

class OrgProductCustomFieldDef(SQLModel, table=True):
    """
    Organisation-defined custom attribute templates.
    Org admins create these once; they appear as extra fields on all product
    edit forms within that org (optionally scoped to specific product types).
    """
    __tablename__ = "org_product_custom_field_defs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(index=True, nullable=False)

    # ── Field definition ──────────────────────────────────────────────────────
    field_name: str = Field(
        max_length=200, index=True,
        description="Internal key, e.g. 'batch_number'. Unique per org.",
    )
    field_label: str = Field(
        max_length=200,
        description="Human-readable label shown in the form, e.g. 'Batch Number'.",
    )
    field_type: str = Field(
        default="text",
        sa_column=Column(String(20), nullable=False),
        description="text | number | date | url | select | boolean | textarea",
    )
    # JSON list of options for 'select' type, e.g. ["Option A", "Option B"]
    options: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    placeholder: Optional[str] = Field(default=None, max_length=300)
    help_text: Optional[str] = Field(default=None, max_length=500)

    # ── Validation ────────────────────────────────────────────────────────────
    is_required: bool = Field(default=False, description="If true, product cannot be published without this field")
    max_length: Optional[int] = Field(default=None, description="Max character length for text/textarea fields")

    # ── Scoping ───────────────────────────────────────────────────────────────
    # Null = applies to ALL product types for this org
    # List = only appears for listed product types, e.g. ["FOOD_AND_BEVERAGE", "GROCERY"]
    applies_to_product_types: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON),
        description="List of ProductType values this field applies to. Null = all types.",
    )

    # ── Display ───────────────────────────────────────────────────────────────
    group: Optional[str] = Field(default=None, max_length=100, description="Section heading in the form")
    position: int = Field(default=0, description="Display order within group")
    unit: Optional[str] = Field(default=None, max_length=50, description="Unit suffix shown in the form, e.g. 'days', 'mg'")

    # ── State ─────────────────────────────────────────────────────────────────
    is_active: bool = Field(default=True)
    created_by: Optional[UUID] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT DOCUMENTS
# PDFs, Markdown files, Word documents — manuals, guides, datasheets,
# safety sheets, certificates, terms of use. Stored in MinIO and referenced here.
#
# Examples:
#   - User Manual (PDF) — attached to a washing machine listing
#   - Installation Guide (PDF/MD) — attached to a router listing
#   - Safety Data Sheet (PDF) — required for chemicals / medication
#   - Service Agreement (PDF) — attached to a maintenance service listing
#   - API Reference (MD) — attached to a DIGITAL_SERVICE listing
#   - Training Syllabus (PDF) — attached to a TRAINING_SERVICE listing
# ══════════════════════════════════════════════════════════════════════════════

class DocumentType(str, Enum):
    MANUAL           = "MANUAL"           # User/operator manual
    INSTALLATION     = "INSTALLATION"     # Setup and installation guide
    DATASHEET        = "DATASHEET"        # Technical specifications sheet
    SAFETY_SHEET     = "SAFETY_SHEET"     # MSDS / safety data sheet
    CERTIFICATE      = "CERTIFICATE"      # Compliance / certification document
    WARRANTY         = "WARRANTY"         # Warranty terms and conditions
    TERMS            = "TERMS"            # Terms of service / use
    API_REFERENCE    = "API_REFERENCE"    # Developer/API documentation (services)
    TRAINING_GUIDE   = "TRAINING_GUIDE"   # Course materials or syllabus
    QUICK_START      = "QUICK_START"      # Quick-start / getting-started guide
    BROCHURE         = "BROCHURE"         # Product brochure / catalogue page
    OTHER            = "OTHER"


class DocumentFormat(str, Enum):
    PDF   = "PDF"
    MD    = "MD"      # Markdown (rendered in-browser)
    DOCX  = "DOCX"
    TXT   = "TXT"
    HTML  = "HTML"


class ProductDocument(SQLModel, table=True):
    """
    A file (PDF, Markdown, DOCX, etc.) attached to a product or service listing.
    Stored in MinIO; this table holds the metadata and download URL.
    """
    __tablename__ = "product_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(index=True, foreign_key="products.product_id")

    # ── File identity ─────────────────────────────────────────────────────────
    title: str = Field(max_length=300, description="Display name, e.g. 'User Manual v2.1'")
    document_type: str = Field(
        default="OTHER",
        sa_column=Column(String(30), nullable=False, index=True),
    )
    file_format: str = Field(
        default="PDF",
        sa_column=Column(String(10), nullable=False),
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    file_url: str = Field(max_length=1000, description="MinIO object URL or signed URL")
    file_size_bytes: Optional[int] = Field(default=None, description="File size for display")
    # Markdown content (optional) — for MD-format docs that are rendered inline
    # If present, file_url may still point to the raw .md file in MinIO
    content_md: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Raw Markdown content — rendered inline on the product page",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    version: Optional[str] = Field(default=None, max_length=50, description="e.g. '2.1', '2026-05'")
    language: str = Field(default="en", max_length=10, description="BCP-47 language tag, e.g. 'en', 'sw'")
    description: Optional[str] = Field(default=None, max_length=500)

    # ── Access control ────────────────────────────────────────────────────────
    is_public: bool = Field(
        default=True,
        description="True = visible to anyone who can view the product (including public scanners). "
                    "False = visible only to org staff.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    uploaded_by: Optional[UUID] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
