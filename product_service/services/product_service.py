from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    BulletPointLimitError,
    DuplicateSkuError,
    ForbiddenError,
    ImageNotFoundError,
    OrgInactiveError,
    OrgNotFoundError,
    ProductNotFoundError,
    ProductNotPublishableError,
    ProductTypeImmutableError,
    ValidationError,
)
from events.producer import ProductProducer
from services.image_index_client import index_product_images as _ai_index_images
from models.product import (
    ListingStatus,
    Product,
    ProductAttribute,
    ProductBulletPoint,
    ProductImage,
    ProductType,
    generate_rsin,
)
from repositories.product_repo import ProductRepository, get_category_attr_model
from schemas.product import (
    ProductCreate,
    ProductUpdate,
)

log = structlog.get_logger(__name__)

_REQUIRED_FOR_PUBLISH = ["title", "brand", "price", "main_image_url"]


class ProductService:
    def __init__(self, db: AsyncSession, producer: ProductProducer) -> None:
        self.repo = ProductRepository(db)
        self.producer = producer

    # ── Guards ────────────────────────────────────────────────────────────────

    async def _assert_org(self, org_id: UUID) -> None:
        org = await self.repo.get_org(org_id)
        if not org:
            raise OrgNotFoundError(detail={"org_id": str(org_id)})
        if not org.is_active:
            raise OrgInactiveError(detail={"org_id": str(org_id)})

    async def _assert_product_belongs_to_org(
        self, product: Product, org_id: UUID, is_platform_admin: bool = False
    ) -> None:
        if not is_platform_admin and product.organisation_id != org_id:
            raise ForbiddenError()

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_product(
        self,
        org_id: UUID,
        data: ProductCreate,
        created_by: str,
    ) -> Product:
        await self._assert_org(org_id)

        if await self.repo.get_by_org_and_sku(org_id, data.seller_sku):
            raise DuplicateSkuError(detail={"seller_sku": data.seller_sku})

        raw = data.model_dump(exclude={"bullet_points", "images", "attributes"})
        # Convert enum values to strings so asyncpg doesn't try to cast to non-existent PG enum types
        for field in ("product_type", "condition", "fulfillment_method", "listing_status", "variation_theme"):
            if field in raw and raw[field] is not None and hasattr(raw[field], "value"):
                raw[field] = raw[field].value
        product = Product(
            rsin=generate_rsin(),
            organisation_id=org_id,
            **raw,
        )
        product = await self.repo.create(product)

        if data.bullet_points:
            await self.repo.replace_bullet_points(
                product.product_id,
                [b.model_dump() for b in data.bullet_points],
            )

        if data.images:
            for img in data.images:
                await self.repo.add_image(
                    ProductImage(product_id=product.product_id, **img.model_dump())
                )

        if data.attributes:
            await self.repo.replace_attributes(
                product.product_id,
                [a.model_dump() for a in data.attributes],
            )

        await self.producer.product_created(product, org_id=org_id, created_by=created_by)
        log.info("product.created", product_id=str(product.product_id), org_id=str(org_id))
        return product

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_product(
        self, product_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        return product

    async def list_products(
        self,
        org_id: UUID,
        is_platform_admin: bool = False,
        product_type: Optional[ProductType] = None,
        listing_status: Optional[ListingStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Product], int]:
        if is_platform_admin:
            return await self.repo.list_all(product_type, listing_status, page, page_size)
        return await self.repo.list_by_org(
            org_id, product_type, listing_status, True, search, page, page_size
        )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_product(
        self,
        product_id: UUID,
        org_id: UUID,
        data: ProductUpdate,
        is_platform_admin: bool = False,
    ) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)

        updates = data.model_dump(exclude_unset=True)

        if "seller_sku" in updates and updates["seller_sku"] != product.seller_sku:
            conflict = await self.repo.get_by_org_and_sku(org_id, updates["seller_sku"])
            if conflict and conflict.product_id != product_id:
                raise DuplicateSkuError(detail={"seller_sku": updates["seller_sku"]})

        updates["updated_at"] = datetime.utcnow()
        product = await self.repo.update(product, updates)
        await self.producer.product_updated(product, org_id=org_id)
        return product

    # ── Publish ───────────────────────────────────────────────────────────────

    async def publish_product(
        self, product_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)

        missing = [f for f in _REQUIRED_FOR_PUBLISH if not getattr(product, f, None)]
        if missing:
            raise ProductNotPublishableError(detail={"missing_fields": missing})

        now = datetime.utcnow()
        await self.repo.update(product, {
            "listing_status": "BUYABLE",
            "published_at": now,
            "updated_at": now,
        })
        await self.producer.product_published(product, org_id=org_id)
        log.info("product.published", product_id=str(product_id), rsin=product.rsin)

        # Index product images into Qdrant for AI counterfeit detection (fire-and-forget)
        images = await self.repo.get_images(product_id)
        if images:
            image_urls  = [img.url for img in images]
            image_roles = [img.role.lower() if img.role else "main" for img in images]
            await _ai_index_images(
                product_id=product_id,
                org_id=org_id,
                image_urls=image_urls,
                title=product.title or "",
                brand=product.brand or "",
                rsin=product.rsin or "",
                image_roles=image_roles,
            )

        return product

    async def deactivate_product(
        self, product_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> None:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        product.is_active = False
        product.listing_status = "INACTIVE"
        self.repo.db.add(product)
        await self.repo.db.flush()
        await self.producer.product_deactivated(product, org_id=org_id)

    # ── Bullet Points ─────────────────────────────────────────────────────────

    async def replace_bullet_points(
        self, product_id: UUID, org_id: UUID, bullets: List[Dict], is_platform_admin: bool = False
    ) -> List[ProductBulletPoint]:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        if len(bullets) > 5:
            raise BulletPointLimitError()
        return await self.repo.replace_bullet_points(product_id, bullets)

    # ── Images ────────────────────────────────────────────────────────────────

    async def add_image(
        self, product_id: UUID, org_id: UUID, img_data: Dict, is_platform_admin: bool = False
    ) -> ProductImage:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        return await self.repo.add_image(ProductImage(product_id=product_id, **img_data))

    async def delete_image(
        self, product_id: UUID, image_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> None:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        image = await self.repo.get_image(image_id)
        if not image or image.product_id != product_id:
            raise ImageNotFoundError()
        await self.repo.delete_image(image)

    # ── Flexible Attributes ───────────────────────────────────────────────────

    async def replace_attributes(
        self, product_id: UUID, org_id: UUID, attrs: List[Dict], is_platform_admin: bool = False
    ) -> List[ProductAttribute]:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        return await self.repo.replace_attributes(product_id, attrs)

    # ── Category Attributes ───────────────────────────────────────────────────

    async def get_category_attrs(self, product_id: UUID, org_id: UUID, is_platform_admin: bool = False) -> Any:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        model = get_category_attr_model(product.product_type)
        if not model:
            return None
        return await self.repo.get_category_attrs(product_id, model)

    async def upsert_category_attrs(
        self, product_id: UUID, org_id: UUID, data: Dict, is_platform_admin: bool = False
    ) -> Any:
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(product, org_id, is_platform_admin)
        model = get_category_attr_model(product.product_type)
        if not model:
            raise ValidationError(message="No category attribute table defined for this product type")
        return await self.repo.upsert_category_attrs(product_id, model, data)

    # ── Variants ──────────────────────────────────────────────────────────────

    async def list_variants(
        self, parent_id: UUID, org_id: UUID, is_platform_admin: bool = False
    ) -> List[Product]:
        parent = await self.repo.get_by_id(parent_id)
        if not parent or not parent.is_active:
            raise ProductNotFoundError()
        await self._assert_product_belongs_to_org(parent, org_id, is_platform_admin)
        return await self.repo.list_variants(parent_id)
