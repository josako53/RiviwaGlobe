"""
api/v1/public.py — Public product endpoints (no authentication).

Called by auth_service's /public/orgs/{id}/products and /public/orgs/{id}/discover
endpoints, and directly by any consumer-facing client that wants to browse a
specific organisation's published catalog.

Routes
──────
  GET /public/products              List published products for an org
  GET /public/products/{product_id} Full detail for a single published product
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.dependencies import DbDep, KafkaDep
from repositories.product_repo import ProductRepository

router = APIRouter(prefix="/public", tags=["Products — Public"])


def _product_list_item(p) -> dict:
    return {
        "product_id":    str(p.product_id),
        "rsin":          p.rsin,
        "product_type":  p.product_type,
        "title":         p.title,
        "brand":         p.brand,
        "price":         str(p.price) if p.price else None,
        "currency":      p.currency,
        "condition":     p.condition,
        "main_image_url": p.main_image_url,
        "listing_status": p.listing_status,
    }


def _product_detail(p, bullets, images, attrs) -> dict:
    return {
        # Core identity
        "product_id":      str(p.product_id),
        "rsin":            p.rsin,
        "seller_sku":      p.seller_sku,
        "product_type":    p.product_type,
        "organisation_id": str(p.organisation_id),

        # Content
        "title":           p.title,
        "brand":           p.brand,
        "manufacturer":    p.manufacturer,
        "model_number":    p.model_number,
        "description":     p.description,
        "usage":           p.usage,

        # Identifiers
        "gtin":            p.gtin,
        "upc":             p.upc,
        "ean":             p.ean,
        "mpn":             p.mpn,
        "industry_unique_id": p.industry_unique_id,
        "industry_id_type":  p.industry_id_type,

        # Origin
        "country_of_origin":   p.country_of_origin,
        "production_location": p.production_location,
        "product_supervisor":  p.product_supervisor,

        # Offer
        "price":           str(p.price) if p.price else None,
        "currency":        p.currency,
        "condition":       p.condition,
        "quantity":        p.quantity,
        "fulfillment_method": p.fulfillment_method,

        # Physical
        "item_weight":     p.item_weight,
        "item_weight_unit": p.item_weight_unit,
        "length":          p.length,
        "width":           p.width,
        "height":          p.height,
        "dimensions_unit": p.dimensions_unit,

        # Primary image
        "main_image_url":  p.main_image_url,

        # Gallery
        "images": [
            {
                "image_id":   str(img.image_id),
                "url":        img.url,
                "role":       img.role,
                "sort_order": img.sort_order,
                "alt_text":   img.alt_text,
            }
            for img in sorted(images, key=lambda x: x.sort_order)
        ],

        # Key features
        "bullet_points": [
            {"position": b.position, "text": b.text}
            for b in sorted(bullets, key=lambda x: x.position)
        ],

        # Flexible attributes
        "attributes": [
            {"name": a.name, "value": a.value, "unit": a.unit}
            for a in attrs
        ],

        # Variation
        "is_parent":         p.is_parent,
        "parent_product_id": str(p.parent_product_id) if p.parent_product_id else None,
        "variation_theme":   p.variation_theme,
        "variation_values":  p.variation_values,

        # Status
        "listing_status": p.listing_status,

        # View-product deep-link
        "view_url": f"https://app.riviwa.com/products/{p.rsin or str(p.product_id)}",

        # Timestamps
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "created_at":   p.created_at.isoformat(),
    }


@router.get("/products", summary="List published products for an organisation")
async def list_public_products(
    db:           DbDep,
    kafka:        KafkaDep,
    org_id:       UUID = Query(..., description="Organisation UUID"),
    product_type: Optional[str] = Query(default=None),
    search:       Optional[str] = Query(default=None, max_length=200),
    page:         int  = Query(default=1, ge=1),
    size:         int  = Query(default=20, ge=1, le=100),
) -> dict:
    """
    Returns published products for the given organisation.
    No authentication needed — only BUYABLE / published listings are shown.
    """
    from models.product import ListingStatus
    repo = ProductRepository(db)
    items, total = await repo.list_by_org(
        org_id=org_id,
        listing_status=ListingStatus.BUYABLE,
        is_active=True,
        product_type=product_type,
        search=search,
        page=page,
        page_size=size,
    )
    return {
        "products": [_product_list_item(p) for p in items],
        "total":    total,
        "page":     page,
        "size":     size,
    }


@router.get("/products/{product_id}", summary="Full detail for a published product")
async def get_public_product(product_id: UUID, db: DbDep, kafka: KafkaDep) -> dict:
    """
    Returns complete product information for a published listing.
    No authentication needed — only BUYABLE listings are visible.
    """
    from models.product import ListingStatus
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id)

    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    if product.listing_status != ListingStatus.BUYABLE.value:
        raise HTTPException(status_code=404, detail="Product is not publicly available.")

    bullets = await repo.get_bullet_points(product_id)
    images  = await repo.get_images(product_id)
    attrs   = await repo.get_attributes(product_id)

    return _product_detail(product, bullets, images, attrs)
