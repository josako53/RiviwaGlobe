"""api/v1/internal.py — Service-to-service product lookup (X-Service-Key only)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import DbDep, KafkaDep, require_internal
from repositories.product_repo import ProductRepository

router = APIRouter(
    prefix="/internal/products",
    tags=["Products — Internal"],
    dependencies=[Depends(require_internal)],
)


@router.get("/{product_id}", summary="Full product detail for service-to-service calls")
async def get_product_internal(product_id: UUID, db: DbDep, kafka: KafkaDep) -> dict:
    """
    Returns the complete product record including images, bullet points, and attributes.
    Called by verification_service to enrich scan responses — consumers see full product
    details (title, images, description, price, brand, RSIN) when they scan a QR code.
    """
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    bullets = await repo.get_bullet_points(product_id)
    images  = await repo.get_images(product_id)
    attrs   = await repo.get_attributes(product_id)

    return {
        # Core identity
        "product_id":        str(product.product_id),
        "rsin":              product.rsin,
        "seller_sku":        product.seller_sku,
        "product_type":      product.product_type,
        "organisation_id":   str(product.organisation_id),

        # Content
        "title":             product.title,
        "brand":             product.brand,
        "manufacturer":      product.manufacturer,
        "model_number":      product.model_number,
        "description":       product.description,
        "usage":             product.usage,

        # Identifiers / barcodes
        "gtin":              product.gtin,
        "upc":               product.upc,
        "ean":               product.ean,
        "isbn":              product.isbn,
        "mpn":               product.mpn,
        "industry_unique_id": product.industry_unique_id,
        "industry_id_type":  product.industry_id_type,

        # Production
        "country_of_origin":    product.country_of_origin,
        "production_location":  product.production_location,
        "product_supervisor":   product.product_supervisor,

        # Offer
        "price":             str(product.price) if product.price else None,
        "currency":          product.currency,
        "condition":         product.condition,
        "quantity":          product.quantity,
        "fulfillment_method": product.fulfillment_method,

        # Physical dimensions
        "item_weight":       product.item_weight,
        "item_weight_unit":  product.item_weight_unit,
        "length":            product.length,
        "width":             product.width,
        "height":            product.height,
        "dimensions_unit":   product.dimensions_unit,

        # Primary image (shown immediately on scan result)
        "main_image_url":    product.main_image_url,

        # All additional images (gallery)
        "images": [
            {
                "image_id":  str(img.image_id),
                "url":       img.url,
                "role":      img.role,
                "sort_order": img.sort_order,
                "alt_text":  img.alt_text,
            }
            for img in sorted(images, key=lambda x: x.sort_order)
        ],

        # Key features (bullet points)
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
        "is_parent":          product.is_parent,
        "parent_product_id":  str(product.parent_product_id) if product.parent_product_id else None,
        "variation_theme":    product.variation_theme,
        "variation_values":   product.variation_values,

        # Status
        "listing_status":     product.listing_status,
        "is_active":          product.is_active,

        # Timestamps
        "created_at":         product.created_at.isoformat(),
        "updated_at":         product.updated_at.isoformat(),
        "published_at":       product.published_at.isoformat() if product.published_at else None,
    }
