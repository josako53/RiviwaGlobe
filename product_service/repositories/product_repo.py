from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.product import (
    ListingStatus,
    OrgCache,
    Product,
    ProductAttribute,
    ProductBulletPoint,
    ProductImage,
    ProductType,
)
from models.category_attributes import (
    ApparelAttributes, AutoPartAttributes, AutomotiveVehicleAttributes,
    BeddingAttributes, ElectronicsAttributes, FoodBeverageAttributes,
    FootwearAttributes, HealthAttributes, HomeKitchenAttributes,
    JewelryWatchAttributes, MediaAttributes, ToyAttributes,
)

log = structlog.get_logger(__name__)

# Maps ProductType values to their category attribute model
_CATEGORY_ATTR_MAP: Dict[str, Any] = {
    # Electronics
    "LAPTOP": ElectronicsAttributes, "DESKTOP": ElectronicsAttributes,
    "TABLET": ElectronicsAttributes, "MONITOR": ElectronicsAttributes,
    "SMARTPHONE": ElectronicsAttributes, "CAMERA": ElectronicsAttributes,
    "HEADPHONE": ElectronicsAttributes, "SPEAKER": ElectronicsAttributes,
    "TV": ElectronicsAttributes, "HOME_THEATER": ElectronicsAttributes,
    "WEARABLE": ElectronicsAttributes, "COMPUTER_COMPONENT": ElectronicsAttributes,
    "NETWORKING_DEVICE": ElectronicsAttributes,
    # Apparel
    "SHIRT": ApparelAttributes, "PANTS": ApparelAttributes, "DRESS": ApparelAttributes,
    "JACKET": ApparelAttributes, "UNDERWEAR": ApparelAttributes,
    "ACTIVEWEAR": ApparelAttributes, "SUIT": ApparelAttributes,
    "TRADITIONAL_WEAR": ApparelAttributes,
    # Footwear
    "SHOES": FootwearAttributes, "SANDALS": FootwearAttributes,
    "BOOTS": FootwearAttributes, "SNEAKERS": FootwearAttributes,
    # Home & Kitchen
    "DRINKING_CUP": HomeKitchenAttributes, "COOKWARE": HomeKitchenAttributes,
    "SMALL_APPLIANCE": HomeKitchenAttributes, "LARGE_APPLIANCE": HomeKitchenAttributes,
    "FURNITURE": HomeKitchenAttributes, "HOME_DECOR": HomeKitchenAttributes,
    "STORAGE": HomeKitchenAttributes, "CLEANING_SUPPLY": HomeKitchenAttributes,
    # Bedding
    "PILLOW": BeddingAttributes, "BEDDING": BeddingAttributes,
    "TOWEL": BeddingAttributes, "MATTRESS": BeddingAttributes,
    # Health
    "SUPPLEMENT": HealthAttributes, "MEDICATION": HealthAttributes,
    "PERSONAL_CARE": HealthAttributes, "MEDICAL_DEVICE": HealthAttributes,
    # Food & Beverage
    "FOOD_AND_BEVERAGE": FoodBeverageAttributes, "GROCERY": FoodBeverageAttributes,
    "ORGANIC_PRODUCT": FoodBeverageAttributes, "FROZEN_FOOD": FoodBeverageAttributes,
    "CHILLED_FOOD": FoodBeverageAttributes, "BEVERAGE": FoodBeverageAttributes,
    "SNACK": FoodBeverageAttributes, "CONDIMENT": FoodBeverageAttributes,
    # Toys
    "TOY": ToyAttributes, "BOARD_GAME": ToyAttributes, "PUZZLE": ToyAttributes,
    "OUTDOOR_TOY": ToyAttributes, "VIDEO_GAME": ToyAttributes,
    # Media
    "BOOK": MediaAttributes, "MUSIC": MediaAttributes, "MOVIE": MediaAttributes,
    "DIGITAL_CONTENT": MediaAttributes,
    # Vehicles
    "CAR_NEW": AutomotiveVehicleAttributes, "CAR_USED": AutomotiveVehicleAttributes,
    "CAR_CERTIFIED": AutomotiveVehicleAttributes, "SUV_NEW": AutomotiveVehicleAttributes,
    "SUV_USED": AutomotiveVehicleAttributes, "TRUCK_NEW": AutomotiveVehicleAttributes,
    "TRUCK_USED": AutomotiveVehicleAttributes, "VAN_NEW": AutomotiveVehicleAttributes,
    "VAN_USED": AutomotiveVehicleAttributes,
    "ELECTRIC_VEHICLE": AutomotiveVehicleAttributes,
    "HYBRID_VEHICLE": AutomotiveVehicleAttributes,
    "MOTORCYCLE": AutomotiveVehicleAttributes, "BUS": AutomotiveVehicleAttributes,
    "MINIBUS": AutomotiveVehicleAttributes,
    # Auto parts
    "AUTO_PART": AutoPartAttributes, "AUTO_ACCESSORY": AutoPartAttributes,
    "TIRE": AutoPartAttributes,
    # Jewelry
    "JEWELRY": JewelryWatchAttributes, "WATCH": JewelryWatchAttributes,
}


def get_category_attr_model(product_type: ProductType) -> Optional[Any]:
    return _CATEGORY_ATTR_MAP.get(product_type.value)


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Org Cache ─────────────────────────────────────────────────────────────

    async def upsert_org_cache(self, org_id: UUID, data: Dict[str, Any]) -> None:
        existing = await self.db.get(OrgCache, org_id)
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            self.db.add(OrgCache(org_id=org_id, **data))

    async def get_org(self, org_id: UUID) -> Optional[OrgCache]:
        return await self.db.get(OrgCache, org_id)

    # ── Product CRUD ──────────────────────────────────────────────────────────

    async def create(self, product: Product) -> Product:
        self.db.add(product)
        await self.db.flush()
        return product

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        return await self.db.get(Product, product_id)

    async def get_by_rsin(self, rsin: str) -> Optional[Product]:
        result = await self.db.execute(select(Product).where(Product.rsin == rsin))
        return result.scalar_one_or_none()

    async def get_by_org_and_sku(self, org_id: UUID, sku: str) -> Optional[Product]:
        result = await self.db.execute(
            select(Product).where(
                Product.organisation_id == org_id,
                Product.seller_sku == sku,
                Product.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: UUID,
        product_type: Optional[ProductType] = None,
        listing_status: Optional[ListingStatus] = None,
        is_active: Optional[bool] = True,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Product], int]:
        q = select(Product).where(Product.organisation_id == org_id)
        if product_type:
            q = q.where(Product.product_type == product_type)
        if listing_status:
            q = q.where(Product.listing_status == listing_status)
        if is_active is not None:
            q = q.where(Product.is_active == is_active)
        if search:
            term = f"%{search}%"
            q = q.where(Product.title.ilike(term) | Product.brand.ilike(term) | Product.seller_sku.ilike(term))

        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        q = q.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def list_all(
        self,
        product_type: Optional[ProductType] = None,
        listing_status: Optional[ListingStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Product], int]:
        q = select(Product).where(Product.is_active == True)
        if product_type:
            q = q.where(Product.product_type == product_type)
        if listing_status:
            q = q.where(Product.listing_status == listing_status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(self, product: Product, data: Dict[str, Any]) -> Product:
        for k, v in data.items():
            setattr(product, k, v)
        self.db.add(product)
        await self.db.flush()
        return product

    async def soft_delete(self, product: Product) -> None:
        product.is_active = False
        product.listing_status = ListingStatus.INACTIVE
        self.db.add(product)
        await self.db.flush()

    # ── Variants ──────────────────────────────────────────────────────────────

    async def list_variants(self, parent_id: UUID) -> List[Product]:
        result = await self.db.execute(
            select(Product).where(Product.parent_product_id == parent_id, Product.is_active == True)
        )
        return result.scalars().all()

    # ── Bullet Points ─────────────────────────────────────────────────────────

    async def get_bullet_points(self, product_id: UUID) -> List[ProductBulletPoint]:
        result = await self.db.execute(
            select(ProductBulletPoint)
            .where(ProductBulletPoint.product_id == product_id)
            .order_by(ProductBulletPoint.position)
        )
        return result.scalars().all()

    async def replace_bullet_points(
        self, product_id: UUID, bullets: List[Dict[str, Any]]
    ) -> List[ProductBulletPoint]:
        existing = await self.get_bullet_points(product_id)
        for b in existing:
            await self.db.delete(b)
        new = [ProductBulletPoint(product_id=product_id, **b) for b in bullets]
        self.db.add_all(new)
        await self.db.flush()
        return new

    # ── Images ────────────────────────────────────────────────────────────────

    async def get_images(self, product_id: UUID) -> List[ProductImage]:
        result = await self.db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.role, ProductImage.position)
        )
        return result.scalars().all()

    async def add_image(self, image: ProductImage) -> ProductImage:
        self.db.add(image)
        await self.db.flush()
        return image

    async def get_image(self, image_id: UUID) -> Optional[ProductImage]:
        return await self.db.get(ProductImage, image_id)

    async def delete_image(self, image: ProductImage) -> None:
        await self.db.delete(image)
        await self.db.flush()

    # ── Flexible Attributes ───────────────────────────────────────────────────

    async def get_attributes(self, product_id: UUID) -> List[ProductAttribute]:
        result = await self.db.execute(
            select(ProductAttribute)
            .where(ProductAttribute.product_id == product_id)
            .order_by(ProductAttribute.group, ProductAttribute.position)
        )
        return result.scalars().all()

    async def replace_attributes(
        self, product_id: UUID, attrs: List[Dict[str, Any]]
    ) -> List[ProductAttribute]:
        existing = await self.get_attributes(product_id)
        for a in existing:
            await self.db.delete(a)
        new = [ProductAttribute(product_id=product_id, **a) for a in attrs]
        self.db.add_all(new)
        await self.db.flush()
        return new

    # ── Category Attributes ───────────────────────────────────────────────────

    async def get_category_attrs(self, product_id: UUID, model: Any) -> Optional[Any]:
        return await self.db.get(model, product_id)

    async def upsert_category_attrs(
        self, product_id: UUID, model: Any, data: Dict[str, Any]
    ) -> Any:
        existing = await self.db.get(model, product_id)
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.db.add(existing)
        else:
            obj = model(product_id=product_id, **data)
            self.db.add(obj)
        await self.db.flush()
        return existing or model(product_id=product_id, **data)
