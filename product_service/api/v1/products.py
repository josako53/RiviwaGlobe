from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from core.dependencies import AdminDep, DbDep, KafkaDep, ManagerDep, StaffDep
from models.product import ListingStatus, ProductType
from repositories.product_repo import ProductRepository
from schemas.product import (
    BulletPointIn,
    ProductAttributeIn,
    ProductAttributeOut,
    ProductBulletPointOut,
    ProductCreate,
    ProductImageIn,
    ProductImageOut,
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

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
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

@router.patch("/{product_id}", response_model=ProductResponse)
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

@router.patch("/{product_id}/publish", response_model=PublishResponse)
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


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
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

@router.put("/{product_id}/bullet-points", response_model=List[BulletPointOut])
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

@router.post("/{product_id}/images", response_model=ProductImageOut, status_code=status.HTTP_201_CREATED)
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


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
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

@router.put("/{product_id}/attributes", response_model=List[ProductAttributeOut])
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


@router.put("/{product_id}/category-attrs")
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

@router.get("/{product_id}/variants", response_model=List[ProductListResponse])
async def list_variants(product_id: UUID, db: DbDep, kafka: KafkaDep, claims: StaffDep):
    """List child variants of a parent product."""
    org_id = UUID(claims.org_id) if claims.org_id else None
    return await _svc(db, kafka).list_variants(product_id, org_id, _is_admin(claims))


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(product, bullets, images, attrs) -> ProductResponse:
    from schemas.product import BulletPointOut, ProductAttributeOut, ProductImageOut
    return ProductResponse(
        **product.model_dump(),
        bullet_points=[BulletPointOut(**b.model_dump()) for b in bullets],
        images=[ProductImageOut(**i.model_dump()) for i in images],
        attributes=[ProductAttributeOut(**a.model_dump()) for a in attrs],
    )
