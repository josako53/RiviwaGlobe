from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.dependencies import AdminDep, DbDep, KafkaDep, ManagerDep, StaffDep, require_feature
from models.product import ListingStatus, ProductType
from repositories.product_repo import ProductRepository
from schemas.product import (
    BulletPointIn,
    OrgCustomFieldDefIn,
    OrgCustomFieldDefOut,
    ProductAttributeIn,
    ProductAttributeOut,
    BulletPointOut,
    ProductCreate,
    ProductDocumentIn,
    ProductDocumentOut,
    ProductDocumentUpdate,
    ProductImageIn,
    ProductImageOut,
    ProductListItem,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    PublishResponse,
)
from services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


def _svc(db: DbDep, kafka: KafkaDep) -> ProductService:
    return ProductService(db, kafka)


def _is_admin(claims: Any) -> bool:
    from core.dependencies import _PLATFORM_ROLE_RANK
    return _PLATFORM_ROLE_RANK.get(claims.platform_role or "", -1) >= 2


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_feature("product_catalog"))])
async def create_product(
    body: ProductCreate,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    """Create a product under the caller's active organisation."""
    org_id = UUID(claims.org_id)
    product = await _svc(db, kafka).create_product(org_id, body, created_by=claims.sub)
    repo = ProductRepository(db)
    bullets = await repo.get_bullet_points(product.product_id)
    images = await repo.get_images(product.product_id)
    attrs = await repo.get_attributes(product.product_id)
    return _to_response(product, bullets, images, attrs)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=ProductListResponse)
async def list_products(
    db: DbDep,
    kafka: KafkaDep,
    claims: StaffDep,
    product_type: Optional[ProductType] = None,
    listing_status: Optional[ListingStatus] = None,
    search: Optional[str] = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List products scoped to the caller's organisation (or all orgs for platform admins)."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    is_admin = _is_admin(claims)
    items, total = await _svc(db, kafka).list_products(
        org_id=org_id,
        is_platform_admin=is_admin,
        product_type=product_type,
        listing_status=listing_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


# ── Org Custom Field Definitions (STATIC — must be before /{product_id}) ─────

@router.get(
    "/org-custom-fields",
    response_model=List[OrgCustomFieldDefOut],
    summary="List org's custom product field definitions",
    description=(
        "Returns all custom attribute field templates defined by this organisation. "
        "These fields appear as extra inputs on the product edit form for all products "
        "in this org (optionally scoped to specific product types)."
    ),
)
async def list_org_custom_fields(
    db: DbDep,
    kafka: KafkaDep,
    claims: StaffDep,
    active_only: bool = Query(default=True),
) -> List[OrgCustomFieldDefOut]:
    from models.product import OrgProductCustomFieldDef
    from sqlalchemy import select
    org_id = UUID(claims.org_id)
    q = select(OrgProductCustomFieldDef).where(OrgProductCustomFieldDef.org_id == org_id)
    if active_only:
        q = q.where(OrgProductCustomFieldDef.is_active == True)
    q = q.order_by(OrgProductCustomFieldDef.group, OrgProductCustomFieldDef.position)
    result = await db.execute(q)
    return [OrgCustomFieldDefOut.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/org-custom-fields",
    response_model=OrgCustomFieldDefOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom product field definition for this org",
    dependencies=[Depends(require_feature("product_catalog"))],
    description=(
        "Define a new custom attribute field for your organisation's products. "
        "Once created, this field appears on the product edit form for all org products "
        "(or only for the specified `applies_to_product_types`).\n\n"
        "**Field types:** `text` | `textarea` | `number` | `date` | `url` | `select` | `boolean`\n\n"
        "**Example use cases:**\n"
        "- Pharmacy: `batch_number` (text, required), `expiry_date` (date, required)\n"
        "- Food org: `halal_certified` (boolean), `nutritional_grade` (select)\n"
        "- NGO: `donor_ref` (text), `project_code` (text)\n"
        "- Manufacturer: `warranty_terms` (textarea), `compliance_standard` (select)"
    ),
)
async def create_org_custom_field(
    body: OrgCustomFieldDefIn,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> OrgCustomFieldDefOut:
    from datetime import datetime
    from models.product import OrgProductCustomFieldDef
    from sqlalchemy import select
    org_id = UUID(claims.org_id)
    existing = (await db.execute(
        select(OrgProductCustomFieldDef).where(
            OrgProductCustomFieldDef.org_id == org_id,
            OrgProductCustomFieldDef.field_name == body.field_name,
        )
    )).scalar_one_or_none()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"error": "FIELD_NAME_EXISTS",
            "detail": f"A field named '{body.field_name}' already exists for this organisation."})
    field = OrgProductCustomFieldDef(org_id=org_id, created_by=claims.sub, **body.model_dump())
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return OrgCustomFieldDefOut.model_validate(field)


@router.patch(
    "/org-custom-fields/{field_id}",
    response_model=OrgCustomFieldDefOut,
    summary="Update a custom field definition",
    dependencies=[Depends(require_feature("product_catalog"))],
)
async def update_org_custom_field(
    field_id: UUID,
    body: dict,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> OrgCustomFieldDefOut:
    from datetime import datetime
    from models.product import OrgProductCustomFieldDef
    org_id = UUID(claims.org_id)
    field = await db.get(OrgProductCustomFieldDef, field_id)
    if not field or field.org_id != org_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"error": "CUSTOM_FIELD_NOT_FOUND"})
    immutable = {"id", "org_id", "created_by", "created_at", "field_name"}
    for k, v in body.items():
        if hasattr(field, k) and k not in immutable:
            setattr(field, k, v)
    field.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(field)
    return OrgCustomFieldDefOut.model_validate(field)


@router.delete(
    "/org-custom-fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a custom field definition",
    dependencies=[Depends(require_feature("product_catalog"))],
)
async def deactivate_org_custom_field(
    field_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> None:
    from models.product import OrgProductCustomFieldDef
    org_id = UUID(claims.org_id)
    field = await db.get(OrgProductCustomFieldDef, field_id)
    if not field or field.org_id != org_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"error": "CUSTOM_FIELD_NOT_FOUND"})
    field.is_active = False
    await db.commit()


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: StaffDep,
):
    org_id = UUID(claims.org_id) if claims.org_id else None
    product = await _svc(db, kafka).get_product(product_id, org_id, _is_admin(claims))
    repo = ProductRepository(db)
    bullets = await repo.get_bullet_points(product_id)
    images = await repo.get_images(product_id)
    attrs = await repo.get_attributes(product_id)
    return _to_response(product, bullets, images, attrs)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{product_id}", response_model=ProductResponse,
              dependencies=[Depends(require_feature("product_catalog"))])
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    org_id = UUID(claims.org_id) if claims.org_id else None
    product = await _svc(db, kafka).update_product(product_id, org_id, body, _is_admin(claims))
    repo = ProductRepository(db)
    bullets = await repo.get_bullet_points(product_id)
    images = await repo.get_images(product_id)
    attrs = await repo.get_attributes(product_id)
    return _to_response(product, bullets, images, attrs)


# ── Publish / Deactivate ──────────────────────────────────────────────────────

@router.patch("/{product_id}/publish", response_model=PublishResponse,
              dependencies=[Depends(require_feature("product_catalog"))])
async def publish_product(
    product_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: AdminDep,
):
    """Move listing status to BUYABLE. Requires title, brand, price, and main image."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    product = await _svc(db, kafka).publish_product(product_id, org_id, _is_admin(claims))
    return PublishResponse(
        product_id=product.product_id,
        rsin=product.rsin,
        listing_status=product.listing_status,
        published_at=product.published_at,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_feature("product_catalog"))])
async def deactivate_product(
    product_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: AdminDep,
):
    """Soft-delete: sets is_active=False and listing_status=INACTIVE."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    await _svc(db, kafka).deactivate_product(product_id, org_id, _is_admin(claims))


# ── Bullet Points ─────────────────────────────────────────────────────────────

@router.put("/{product_id}/bullet-points", response_model=List[BulletPointOut],
            dependencies=[Depends(require_feature("product_catalog"))])
async def replace_bullet_points(
    product_id: UUID,
    body: List[BulletPointIn],
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    """Replace all bullet points (max 5). Positions must be 1–5."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    bullets = await _svc(db, kafka).replace_bullet_points(
        product_id, org_id, [b.model_dump() for b in body], _is_admin(claims)
    )
    return bullets


@router.get("/{product_id}/bullet-points", response_model=List[BulletPointOut])
async def get_bullet_points(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    repo = ProductRepository(db)
    return await repo.get_bullet_points(product_id)


# ── Images ────────────────────────────────────────────────────────────────────

@router.post("/{product_id}/images", response_model=ProductImageOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_feature("product_catalog"))])
async def add_image(
    product_id: UUID,
    body: ProductImageIn,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    org_id = UUID(claims.org_id) if claims.org_id else None
    return await _svc(db, kafka).add_image(product_id, org_id, body.model_dump(), _is_admin(claims))


@router.get("/{product_id}/images", response_model=List[ProductImageOut])
async def get_images(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    return await ProductRepository(db).get_images(product_id)


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_feature("product_catalog"))])
async def delete_image(
    product_id: UUID,
    image_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    org_id = UUID(claims.org_id) if claims.org_id else None
    await _svc(db, kafka).delete_image(product_id, image_id, org_id, _is_admin(claims))


# ── Flexible Attributes ───────────────────────────────────────────────────────

@router.put("/{product_id}/attributes", response_model=List[ProductAttributeOut],
            dependencies=[Depends(require_feature("product_catalog"))])
async def replace_attributes(
    product_id: UUID,
    body: List[ProductAttributeIn],
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    """Replace all name-value attributes. Used for any custom/industry-specific fields."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    return await _svc(db, kafka).replace_attributes(
        product_id, org_id, [a.model_dump() for a in body], _is_admin(claims)
    )


@router.get("/{product_id}/attributes", response_model=List[ProductAttributeOut])
async def get_attributes(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    return await ProductRepository(db).get_attributes(product_id)


# ── Category-Specific Attributes ──────────────────────────────────────────────

@router.get("/{product_id}/category-attrs")
async def get_category_attrs(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    """Returns the category-specific attribute record (schema varies by product_type)."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    attrs = await _svc(db, kafka).get_category_attrs(product_id, org_id, _is_admin(claims))
    if attrs is None:
        return {}
    return attrs.model_dump(exclude={"product_id"})


@router.put("/{product_id}/category-attrs",
            dependencies=[Depends(require_feature("product_catalog"))])
async def upsert_category_attrs(
    product_id: UUID,
    body: Dict[str, Any],
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
):
    """Create or update category-specific attributes. Fields accepted depend on product_type."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    attrs = await _svc(db, kafka).upsert_category_attrs(product_id, org_id, body, _is_admin(claims))
    return attrs.model_dump(exclude={"product_id"})


# ── Variants ──────────────────────────────────────────────────────────────────

@router.get("/{product_id}/variants", response_model=List[ProductListItem])
async def list_variants(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    """List child variants of a parent product."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    return await _svc(db, kafka).list_variants(product_id, org_id, _is_admin(claims))


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(product, bullets, images, attrs, docs=None) -> ProductResponse:
    from schemas.product import BulletPointOut, ProductAttributeOut, ProductDocumentOut, ProductImageOut
    return ProductResponse(
        **product.model_dump(),
        bullet_points=[BulletPointOut(**b.model_dump()) for b in bullets],
        images=[ProductImageOut(**i.model_dump()) for i in images],
        attributes=[ProductAttributeOut(**a.model_dump()) for a in attrs],
        documents=[ProductDocumentOut(**d.model_dump()) for d in (docs or [])],
    )


# ── Product Documents ─────────────────────────────────────────────────────────

@router.get(
    "/{product_id}/documents",
    response_model=List[ProductDocumentOut],
    summary="List documents attached to a product",
    description=(
        "Returns all documents (PDFs, Markdown guides, manuals) attached to a product or service listing. "
        "Public documents are visible to anyone who can view the product (including scanners). "
        "Private documents require org staff access."
    ),
)
async def list_documents(
    product_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: StaffDep,
    public_only: bool = Query(default=False),
) -> List[ProductDocumentOut]:
    from models.product import ProductDocument
    from sqlalchemy import select
    q = select(ProductDocument).where(ProductDocument.product_id == product_id)
    if public_only:
        q = q.where(ProductDocument.is_public == True)
    q = q.order_by(ProductDocument.document_type, ProductDocument.created_at)
    result = await db.execute(q)
    return [ProductDocumentOut.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/{product_id}/documents",
    response_model=ProductDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a document to a product",
    dependencies=[Depends(require_feature("product_catalog"))],
    description=(
        "Attach a manual, installation guide, datasheet, safety sheet, or any other document "
        "to a product or service listing.\n\n"
        "**Supported document types:** MANUAL | INSTALLATION | DATASHEET | SAFETY_SHEET | "
        "CERTIFICATE | WARRANTY | TERMS | API_REFERENCE | TRAINING_GUIDE | QUICK_START | BROCHURE | OTHER\n\n"
        "**Supported formats:** PDF | MD | DOCX | TXT | HTML\n\n"
        "Upload the file to MinIO first, then provide the URL here. "
        "For Markdown documents, you can also pass `content_md` to render the guide inline on the product page."
    ),
)
async def add_document(
    product_id: UUID,
    body: ProductDocumentIn,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> ProductDocumentOut:
    from datetime import datetime
    from models.product import ProductDocument
    doc = ProductDocument(
        product_id=product_id,
        uploaded_by=claims.sub,
        **body.model_dump(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return ProductDocumentOut.model_validate(doc)


@router.patch(
    "/{product_id}/documents/{doc_id}",
    response_model=ProductDocumentOut,
    summary="Update document metadata or replace file URL",
    dependencies=[Depends(require_feature("product_catalog"))],
)
async def update_document(
    product_id: UUID,
    doc_id: UUID,
    body: ProductDocumentUpdate,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> ProductDocumentOut:
    from datetime import datetime
    from models.product import ProductDocument
    doc = await db.get(ProductDocument, doc_id)
    if not doc or doc.product_id != product_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"error": "DOCUMENT_NOT_FOUND"})
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(doc, k, v)
    doc.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(doc)
    return ProductDocumentOut.model_validate(doc)


@router.delete(
    "/{product_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a document from a product",
    dependencies=[Depends(require_feature("product_catalog"))],
)
async def delete_document(
    product_id: UUID,
    doc_id: UUID,
    db: DbDep,
    kafka: KafkaDep,
    claims: ManagerDep,
) -> None:
    from models.product import ProductDocument
    doc = await db.get(ProductDocument, doc_id)
    if not doc or doc.product_id != product_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"error": "DOCUMENT_NOT_FOUND"})
    await db.delete(doc)
    await db.commit()
