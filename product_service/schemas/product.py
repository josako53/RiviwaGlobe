from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from models.product import (
    DocumentFormat,
    DocumentType,
    FulfillmentMethod,
    ImageRole,
    ListingStatus,
    ProductCondition,
    ProductType,
    VariationTheme,
)


# ── Bullet Points ─────────────────────────────────────────────────────────────

class BulletPointIn(BaseModel):
    position: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=500)


class BulletPointOut(BulletPointIn):
    id: UUID


# ── Images ────────────────────────────────────────────────────────────────────

class ProductImageIn(BaseModel):
    role: ImageRole = ImageRole.ALTERNATE
    position: int = Field(default=1, ge=1)
    url: str = Field(min_length=1, max_length=1000)
    alt_text: Optional[str] = Field(default=None, max_length=200)


class ProductImageOut(ProductImageIn):
    id: UUID


# ── Flexible Name–Value Attributes ────────────────────────────────────────────

class ProductAttributeIn(BaseModel):
    attribute_name: str = Field(min_length=1, max_length=200)
    attribute_value: str = Field(min_length=1, max_length=1000)
    unit: Optional[str] = Field(default=None, max_length=50)
    group: Optional[str] = Field(default=None, max_length=100)
    position: int = Field(default=0)
    is_searchable: bool = False


class ProductAttributeOut(ProductAttributeIn):
    id: UUID


# ── Product Create ────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    # Classification (immutable after publish)
    product_type: ProductType
    browse_node_id: Optional[str] = Field(default=None, max_length=50)
    browse_node_path: Optional[str] = Field(default=None, max_length=500)
    item_type_keyword: Optional[str] = Field(default=None, max_length=200)

    # Identifiers
    seller_sku: str = Field(min_length=1, max_length=100)
    upc: Optional[str] = Field(default=None, max_length=20)
    ean: Optional[str] = Field(default=None, max_length=20)
    gtin: Optional[str] = Field(default=None, max_length=20)
    isbn: Optional[str] = Field(default=None, max_length=20)
    mpn: Optional[str] = Field(default=None, max_length=100)
    industry_unique_id: Optional[str] = Field(default=None, max_length=100)
    industry_id_type: Optional[str] = Field(default=None, max_length=50)

    # Core content
    title: str = Field(min_length=1, max_length=500)
    brand: str = Field(min_length=1, max_length=200)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model_number: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    usage: Optional[str] = Field(default=None, max_length=2000)
    how_to_use: Optional[str] = Field(
        default=None,
        description="Step-by-step usage/installation instructions. Supports Markdown.",
    )

    # Production
    production_location: Optional[str] = Field(default=None, max_length=300)
    country_of_origin: Optional[str] = Field(default=None, max_length=100)
    made_in: Optional[str] = Field(
        default=None, max_length=150,
        description="Display label e.g. 'Made in Tanzania', 'Assembled in Kenya'.",
    )
    product_supervisor: Optional[str] = Field(default=None, max_length=200)

    # Offer
    price: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="TZS", max_length=3)
    condition: ProductCondition = ProductCondition.NEW
    quantity: int = Field(default=0, ge=0)
    fulfillment_method: FulfillmentMethod = FulfillmentMethod.MERCHANT

    # Physical
    item_weight: Optional[float] = Field(default=None, gt=0)
    item_weight_unit: str = Field(default="kg", max_length=10)
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    dimensions_unit: str = Field(default="cm", max_length=10)

    # Image
    main_image_url: Optional[str] = Field(default=None, max_length=1000)

    # Variation
    is_parent: bool = False
    parent_product_id: Optional[UUID] = None
    variation_theme: Optional[VariationTheme] = None
    variation_values: Optional[Dict[str, Any]] = None

    # Initial content (optional — can be added via separate endpoints)
    bullet_points: Optional[List[BulletPointIn]] = Field(default=None, max_length=5)
    images: Optional[List[ProductImageIn]] = None
    attributes: Optional[List[ProductAttributeIn]] = None

    @field_validator("bullet_points")
    @classmethod
    def max_five_bullets(cls, v: Optional[List]) -> Optional[List]:
        if v and len(v) > 5:
            raise ValueError("Maximum 5 bullet points allowed")
        return v


# ── Product Update ────────────────────────────────────────────────────────────

class ProductUpdate(BaseModel):
    """All fields optional. product_type is excluded — it is immutable after publish."""
    browse_node_id: Optional[str] = Field(default=None, max_length=50)
    browse_node_path: Optional[str] = Field(default=None, max_length=500)
    item_type_keyword: Optional[str] = Field(default=None, max_length=200)

    seller_sku: Optional[str] = Field(default=None, max_length=100)
    upc: Optional[str] = Field(default=None, max_length=20)
    ean: Optional[str] = Field(default=None, max_length=20)
    gtin: Optional[str] = Field(default=None, max_length=20)
    isbn: Optional[str] = Field(default=None, max_length=20)
    mpn: Optional[str] = Field(default=None, max_length=100)
    industry_unique_id: Optional[str] = Field(default=None, max_length=100)
    industry_id_type: Optional[str] = Field(default=None, max_length=50)

    title: Optional[str] = Field(default=None, max_length=500)
    brand: Optional[str] = Field(default=None, max_length=200)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model_number: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    usage: Optional[str] = Field(default=None, max_length=2000)
    how_to_use: Optional[str] = Field(default=None)

    production_location: Optional[str] = Field(default=None, max_length=300)
    country_of_origin: Optional[str] = Field(default=None, max_length=100)
    made_in: Optional[str] = Field(default=None, max_length=150)
    product_supervisor: Optional[str] = Field(default=None, max_length=200)

    price: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(default=None, max_length=3)
    condition: Optional[ProductCondition] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    fulfillment_method: Optional[FulfillmentMethod] = None

    item_weight: Optional[float] = Field(default=None, gt=0)
    item_weight_unit: Optional[str] = Field(default=None, max_length=10)
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    dimensions_unit: Optional[str] = Field(default=None, max_length=10)
    main_image_url: Optional[str] = Field(default=None, max_length=1000)
    variation_theme: Optional[VariationTheme] = None
    variation_values: Optional[Dict[str, Any]] = None


# ── Product Response ──────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    product_id: UUID
    rsin: Optional[str]
    organisation_id: UUID

    # Classification
    product_type: ProductType
    browse_node_id: Optional[str]
    browse_node_path: Optional[str]
    item_type_keyword: Optional[str]

    # Identifiers
    seller_sku: str
    upc: Optional[str]
    ean: Optional[str]
    gtin: Optional[str]
    isbn: Optional[str]
    mpn: Optional[str]
    industry_unique_id: Optional[str]
    industry_id_type: Optional[str]

    # Content
    title: str
    brand: str
    manufacturer: Optional[str]
    model_number: Optional[str]
    description: Optional[str]
    usage: Optional[str]
    how_to_use: Optional[str]

    # Production
    production_location: Optional[str]
    country_of_origin: Optional[str]
    made_in: Optional[str]
    product_supervisor: Optional[str]

    # Offer
    price: Decimal
    currency: str
    condition: ProductCondition
    quantity: int
    fulfillment_method: FulfillmentMethod

    # Physical
    item_weight: Optional[float]
    item_weight_unit: str
    length: Optional[float]
    width: Optional[float]
    height: Optional[float]
    dimensions_unit: str

    # Image
    main_image_url: Optional[str]

    # Variation
    is_parent: bool
    parent_product_id: Optional[UUID]
    variation_theme: Optional[VariationTheme]
    variation_values: Optional[Dict[str, Any]]

    # Status
    listing_status: ListingStatus
    is_active: bool
    is_gated: bool
    suppression_reason: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    # Related (populated on detail fetch)
    bullet_points: List[BulletPointOut] = []
    images: List[ProductImageOut] = []
    attributes: List[ProductAttributeOut] = []
    documents: List["ProductDocumentOut"] = []

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    product_id: UUID
    rsin: Optional[str]
    organisation_id: UUID
    product_type: ProductType
    seller_sku: str
    title: str
    brand: str
    price: Decimal
    currency: str
    condition: ProductCondition
    quantity: int
    listing_status: ListingStatus
    is_active: bool
    main_image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: List[ProductListItem]
    total: int
    page: int
    page_size: int
    pages: int


class PublishResponse(BaseModel):
    product_id: UUID
    rsin: str
    listing_status: ListingStatus
    published_at: datetime


# ── Org Custom Field Definitions ──────────────────────────────────────────────

class OrgCustomFieldDefIn(BaseModel):
    field_name:   str  = Field(min_length=1, max_length=200, description="Internal key, e.g. 'batch_number'")
    field_label:  str  = Field(min_length=1, max_length=200, description="Form label, e.g. 'Batch Number'")
    field_type:   str  = Field(default="text", description="text | number | date | url | select | boolean | textarea")
    options:      Optional[List[Any]] = Field(default=None, description="For select type: ['Option A', 'Option B']")
    placeholder:  Optional[str] = Field(default=None, max_length=300)
    help_text:    Optional[str] = Field(default=None, max_length=500)
    is_required:  bool = False
    max_length:   Optional[int] = None
    applies_to_product_types: Optional[List[str]] = Field(
        default=None,
        description="List of ProductType values. Null = applies to all product types.",
    )
    group:    Optional[str] = Field(default=None, max_length=100)
    position: int = 0
    unit:     Optional[str] = Field(default=None, max_length=50)


class OrgCustomFieldDefOut(OrgCustomFieldDefIn):
    id:         UUID
    org_id:     UUID
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Product Documents ─────────────────────────────────────────────────────────

class ProductDocumentIn(BaseModel):
    title:         str           = Field(min_length=1, max_length=300)
    document_type: DocumentType  = DocumentType.OTHER
    file_format:   DocumentFormat = DocumentFormat.PDF
    file_url:      str           = Field(min_length=1, max_length=1000, description="MinIO URL or signed URL")
    file_size_bytes: Optional[int] = None
    content_md:    Optional[str] = Field(default=None, description="Raw Markdown content (for MD format docs)")
    version:       Optional[str] = Field(default=None, max_length=50)
    language:      str           = Field(default="en", max_length=10)
    description:   Optional[str] = Field(default=None, max_length=500)
    is_public:     bool          = True


class ProductDocumentOut(ProductDocumentIn):
    id:          UUID
    product_id:  UUID
    uploaded_by: Optional[UUID]
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


class ProductDocumentUpdate(BaseModel):
    title:         Optional[str]           = Field(default=None, max_length=300)
    document_type: Optional[DocumentType]  = None
    file_url:      Optional[str]           = Field(default=None, max_length=1000)
    file_size_bytes: Optional[int]         = None
    content_md:    Optional[str]           = None
    version:       Optional[str]           = Field(default=None, max_length=50)
    language:      Optional[str]           = Field(default=None, max_length=10)
    description:   Optional[str]           = Field(default=None, max_length=500)
    is_public:     Optional[bool]          = None
