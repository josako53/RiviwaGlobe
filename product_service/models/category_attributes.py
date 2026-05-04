"""
models/category_attributes.py — Category-specific attribute tables.

Each table maps 1-to-1 with a Product (via product_id FK).
The applicable table is determined by Product.product_type:

  ProductType.LAPTOP / DESKTOP / TABLET / SMARTPHONE / ...  → ElectronicsAttributes
  ProductType.SHIRT / PANTS / DRESS / ...                   → ApparelAttributes
  ProductType.SHOES / SANDALS / BOOTS / ...                 → FootwearAttributes
  ProductType.DRINKING_CUP / COOKWARE / FURNITURE / ...     → HomeKitchenAttributes
  ProductType.PILLOW / BEDDING / TOWEL / ...                → BeddingAttributes
  ProductType.SUPPLEMENT / MEDICATION / ...                 → HealthAttributes
  ProductType.FOOD_AND_BEVERAGE / GROCERY / BEVERAGE / ...  → FoodBeverageAttributes
  ProductType.TOY / BOARD_GAME / PUZZLE / ...               → ToyAttributes
  ProductType.BOOK / MUSIC / MOVIE / ...                    → MediaAttributes
  ProductType.CAR_NEW / CAR_USED / SUV_* / TRUCK_* / ...   → AutomotiveVehicleAttributes
  ProductType.AUTO_PART / AUTO_ACCESSORY / TIRE             → AutoPartAttributes
  ProductType.JEWELRY / WATCH                               → JewelryWatchAttributes

Required vs optional fields follow the same rules as Amazon's SP-API JSON schemas:
a listing cannot move to BUYABLE status until all required fields are populated.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# ══════════════════════════════════════════════════════════════════════════════
# 1. ELECTRONICS
#    Covers: LAPTOP, DESKTOP, TABLET, MONITOR, SMARTPHONE, CAMERA,
#            HEADPHONE, SPEAKER, TV, HOME_THEATER, WEARABLE,
#            COMPUTER_COMPONENT, NETWORKING_DEVICE
# ══════════════════════════════════════════════════════════════════════════════

class ElectronicsAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_electronics"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    processor_brand: Optional[str] = Field(default=None, max_length=100, description="e.g. Intel, AMD, Apple M")
    processor_model: Optional[str] = Field(default=None, max_length=100, description="e.g. Core i7-1365U")
    ram_gb: Optional[int] = Field(default=None, description="RAM in GB")
    storage_gb: Optional[int] = Field(default=None, description="Primary storage in GB")
    storage_type: Optional[str] = Field(default=None, max_length=50, description="SSD, HDD, eMMC, NVMe")
    display_size_inches: Optional[float] = Field(default=None, description="Screen diagonal in inches")
    display_resolution: Optional[str] = Field(default=None, max_length=50, description="e.g. 1920x1080, 4K")
    display_type: Optional[str] = Field(default=None, max_length=50, description="IPS, OLED, AMOLED, VA")
    operating_system: Optional[str] = Field(default=None, max_length=100, description="e.g. Windows 11, macOS Ventura, Android 14")
    connectivity: Optional[str] = Field(default=None, max_length=200, description="e.g. Wi-Fi 6, Bluetooth 5.3, 5G")
    battery_life_hours: Optional[float] = Field(default=None, description="Rated battery life in hours")
    battery_capacity_mah: Optional[int] = Field(default=None, description="Battery capacity in mAh")

    # Recommended
    color: Optional[str] = Field(default=None, max_length=100)
    ports: Optional[str] = Field(default=None, max_length=300, description="e.g. 2x USB-C, 1x HDMI, 3.5mm")
    graphics_card: Optional[str] = Field(default=None, max_length=100)
    refresh_rate_hz: Optional[int] = Field(default=None)
    camera_mp: Optional[float] = Field(default=None, description="Main camera megapixels")
    water_resistance_rating: Optional[str] = Field(default=None, max_length=20, description="e.g. IP68")
    form_factor: Optional[str] = Field(default=None, max_length=50, description="e.g. Tower, Mini-ITX, 2-in-1")

    # Optional
    compatible_devices: Optional[str] = Field(default=None, max_length=300)
    included_accessories: Optional[str] = Field(default=None, max_length=300)
    voltage: Optional[str] = Field(default=None, max_length=20, description="e.g. 100-240V")
    wattage: Optional[float] = Field(default=None)
    special_features: Optional[str] = Field(default=None, max_length=300, description="e.g. Backlit keyboard, Face ID, Stylus support")


# ══════════════════════════════════════════════════════════════════════════════
# 2. APPAREL
#    Covers: SHIRT, PANTS, DRESS, JACKET, UNDERWEAR, ACTIVEWEAR,
#            SUIT, TRADITIONAL_WEAR
# ══════════════════════════════════════════════════════════════════════════════

class ApparelAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_apparel"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    size: Optional[str] = Field(default=None, max_length=50, description="e.g. S, M, L, XL, 32W/30L")
    color: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=50, description="Men's, Women's, Boys', Girls', Baby, Unisex")
    material: Optional[str] = Field(default=None, max_length=200, description="e.g. 100% Cotton, 80% Polyester 20% Elastane")
    closure_type: Optional[str] = Field(default=None, max_length=100, description="e.g. Button, Zipper, Pull-On, Hook & Eye")

    # Recommended
    fabric_type: Optional[str] = Field(default=None, max_length=100, description="e.g. Woven, Knit, Denim, Jersey")
    care_instructions: Optional[str] = Field(default=None, max_length=300, description="e.g. Machine wash cold, Tumble dry low")
    fit_type: Optional[str] = Field(default=None, max_length=50, description="e.g. Slim, Regular, Relaxed, Oversized")
    neckline: Optional[str] = Field(default=None, max_length=50)
    sleeve_type: Optional[str] = Field(default=None, max_length=50, description="e.g. Short, Long, Sleeveless, 3/4")
    pattern: Optional[str] = Field(default=None, max_length=100, description="e.g. Solid, Striped, Plaid, Floral")
    occasion: Optional[str] = Field(default=None, max_length=100, description="e.g. Casual, Formal, Sportswear, Traditional")

    # Optional
    size_system: Optional[str] = Field(default=None, max_length=20, description="e.g. US, EU, UK, AU, Swahili/African sizing")
    chest_cm: Optional[float] = Field(default=None)
    waist_cm: Optional[float] = Field(default=None)
    hip_cm: Optional[float] = Field(default=None)
    inseam_cm: Optional[float] = Field(default=None)
    length_cm: Optional[float] = Field(default=None)
    country_size_map: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="{'US': 'L', 'EU': '42', 'UK': '16'}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. FOOTWEAR
#    Covers: SHOES, SANDALS, BOOTS, SNEAKERS
# ══════════════════════════════════════════════════════════════════════════════

class FootwearAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_footwear"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    shoe_size: Optional[str] = Field(default=None, max_length=20, description="e.g. 42, 9 US, 8 UK")
    shoe_size_system: Optional[str] = Field(default=None, max_length=20, description="US, EU, UK, CM")
    shoe_width: Optional[str] = Field(default=None, max_length=20, description="Narrow, Regular, Wide, Extra Wide")
    color: Optional[str] = Field(default=None, max_length=100)
    outer_material: Optional[str] = Field(default=None, max_length=100, description="e.g. Leather, Suede, Canvas, Mesh")
    sole_material: Optional[str] = Field(default=None, max_length=100, description="e.g. Rubber, EVA, TPU")
    closure_type: Optional[str] = Field(default=None, max_length=100, description="e.g. Lace-Up, Slip-On, Velcro, Buckle")
    target_gender: Optional[str] = Field(default=None, max_length=50, description="Men, Women, Unisex, Boys, Girls")

    # Recommended
    heel_height_cm: Optional[float] = Field(default=None)
    heel_type: Optional[str] = Field(default=None, max_length=50, description="e.g. Flat, Block, Stiletto, Wedge")
    toe_shape: Optional[str] = Field(default=None, max_length=50, description="e.g. Round, Pointed, Square, Open")
    lining_material: Optional[str] = Field(default=None, max_length=100)
    waterproof: Optional[bool] = Field(default=None)
    occasion: Optional[str] = Field(default=None, max_length=100)

    # Optional
    platform_height_cm: Optional[float] = Field(default=None)
    shaft_height_cm: Optional[float] = Field(default=None, description="Boot shaft measurement")


# ══════════════════════════════════════════════════════════════════════════════
# 4. HOME & KITCHEN
#    Covers: DRINKING_CUP, COOKWARE, SMALL_APPLIANCE, LARGE_APPLIANCE,
#            FURNITURE, HOME_DECOR, STORAGE, CLEANING_SUPPLY
# ══════════════════════════════════════════════════════════════════════════════

class HomeKitchenAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_home_kitchen"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    material: Optional[str] = Field(default=None, max_length=200, description="e.g. Stainless Steel, BPA-Free Plastic, Ceramic")
    color: Optional[str] = Field(default=None, max_length=100)
    item_count: Optional[int] = Field(default=None, description="Number of pieces in the set")

    # Recommended
    capacity_ml: Optional[float] = Field(default=None, description="Liquid capacity in mL (cups, pots, etc.)")
    capacity_unit: Optional[str] = Field(default="ml", max_length=20)
    dishwasher_safe: Optional[bool] = Field(default=None)
    microwave_safe: Optional[bool] = Field(default=None)
    oven_safe: Optional[bool] = Field(default=None)
    oven_safe_temp_celsius: Optional[int] = Field(default=None)
    compatible_stove_types: Optional[str] = Field(default=None, max_length=200, description="Gas, Electric, Induction, All")
    finish_type: Optional[str] = Field(default=None, max_length=100, description="e.g. Matte, Glossy, Non-stick, Polished")
    assembly_required: Optional[bool] = Field(default=None)
    number_of_shelves: Optional[int] = Field(default=None)
    weight_capacity_kg: Optional[float] = Field(default=None)

    # Optional
    wattage: Optional[float] = Field(default=None, description="For appliances")
    voltage: Optional[str] = Field(default=None, max_length=20)
    included_components: Optional[str] = Field(default=None, max_length=300)
    style: Optional[str] = Field(default=None, max_length=100, description="e.g. Modern, Traditional, Rustic, Minimalist")


# ══════════════════════════════════════════════════════════════════════════════
# 5. BEDDING & BATH
#    Covers: PILLOW, BEDDING, TOWEL, MATTRESS
# ══════════════════════════════════════════════════════════════════════════════

class BeddingAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_bedding"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    size: Optional[str] = Field(default=None, max_length=50, description="e.g. Twin, Full, Queen, King, 50x70cm")
    color: Optional[str] = Field(default=None, max_length=100)
    fill_material: Optional[str] = Field(default=None, max_length=100, description="e.g. Down, Memory Foam, Polyester Fill")
    item_count: Optional[int] = Field(default=None, description="e.g. 2 for a pillowcase pair")
    care_instructions: Optional[str] = Field(default=None, max_length=300)

    # Recommended
    thread_count: Optional[int] = Field(default=None, description="For sheets and pillowcases")
    material: Optional[str] = Field(default=None, max_length=200, description="e.g. 100% Egyptian Cotton, Bamboo, Microfiber")
    fill_power: Optional[int] = Field(default=None, description="Down fill power (loft rating)")
    firmness: Optional[str] = Field(default=None, max_length=50, description="Soft, Medium, Firm — for pillows & mattresses")
    mattress_type: Optional[str] = Field(default=None, max_length=100, description="Innerspring, Memory Foam, Latex, Hybrid")
    mattress_depth_cm: Optional[float] = Field(default=None)

    # Optional
    pattern: Optional[str] = Field(default=None, max_length=100)
    hypoallergenic: Optional[bool] = Field(default=None)
    cooling_technology: Optional[str] = Field(default=None, max_length=100)


# ══════════════════════════════════════════════════════════════════════════════
# 6. HEALTH & PERSONAL CARE
#    Covers: SUPPLEMENT, MEDICATION, PERSONAL_CARE, MEDICAL_DEVICE
# ══════════════════════════════════════════════════════════════════════════════

class HealthAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_health"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    active_ingredients: Optional[str] = Field(default=None, sa_column=Column("active_ingredients", JSON), description="List of active ingredients with amounts")
    dosage_form: Optional[str] = Field(default=None, max_length=100, description="e.g. Tablet, Capsule, Liquid, Topical, Patch")
    item_count: Optional[int] = Field(default=None, description="e.g. 60 capsules, 30 tablets")
    directions: Optional[str] = Field(default=None, max_length=1000, description="Dosage and usage directions")
    warnings: Optional[str] = Field(default=None, max_length=1000, description="Safety warnings and contraindications")
    age_range: Optional[str] = Field(default=None, max_length=50, description="e.g. Adults 18+, Children 6-12")

    # Recommended
    drug_facts: Optional[dict] = Field(default=None, sa_column=Column("drug_facts", JSON))
    inactive_ingredients: Optional[str] = Field(default=None, max_length=500)
    allergen_information: Optional[str] = Field(default=None, max_length=300)
    storage_instructions: Optional[str] = Field(default=None, max_length=300)
    expiration_date: Optional[date] = Field(default=None)
    lot_number: Optional[str] = Field(default=None, max_length=100)
    regulatory_approval: Optional[str] = Field(default=None, max_length=200, description="e.g. TFDA approved, CE marked, FDA registered")
    is_prescription_required: Optional[bool] = Field(default=False)

    # Optional
    flavor: Optional[str] = Field(default=None, max_length=100)
    unit_count: Optional[float] = Field(default=None)
    unit_count_type: Optional[str] = Field(default=None, max_length=30, description="mg, mcg, IU, g")


# ══════════════════════════════════════════════════════════════════════════════
# 7. FOOD & BEVERAGE
#    Covers: FOOD_AND_BEVERAGE, GROCERY, ORGANIC_PRODUCT, FROZEN_FOOD,
#            CHILLED_FOOD, BEVERAGE, SNACK, CONDIMENT
#    Gated category — requires health authority compliance proof.
# ══════════════════════════════════════════════════════════════════════════════

class FoodBeverageAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_food_beverage"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required — food-specific fields that no other category has
    is_expirable: bool = Field(default=True, description="Whether the product has an expiry date")
    expiration_date: Optional[date] = Field(default=None, description="Must be permanently marked on unit")
    fulfillment_center_shelf_life_days: Optional[int] = Field(default=None, ge=0, le=1825, description="Days product can sit in fulfilment centre (0–1,825)")

    # Required content
    ingredients: Optional[str] = Field(default=None, sa_column=Column(JSON), description="Ingredient list — also required as a secondary product image")
    nutrition_facts: Optional[dict] = Field(default=None, sa_column=Column("nutrition_facts", JSON), description="Full nutrition facts panel — also required as a secondary product image")
    allergen_information: Optional[str] = Field(default=None, max_length=500, description="e.g. Contains: Gluten, Dairy, Tree Nuts")
    dietary_claims: Optional[list] = Field(default=None, sa_column=Column("dietary_claims", JSON), description="['Organic','Kosher','Gluten-Free','Halal'] — must match physical packaging")

    # Required offer fields (mandatory for all new grocery listings)
    item_package_quantity: Optional[int] = Field(default=None, description="Multi-pack unit count")
    unit_count: Optional[float] = Field(default=None, description="Weight or volume per unit e.g. 500")
    unit_count_type: Optional[str] = Field(default=None, max_length=20, description="g, ml, oz, fl oz, count")
    price_per_unit: Optional[str] = Field(default=None, max_length=50, description="Calculated display field e.g. TZS 2,000/kg")

    # Recommended
    flavor: Optional[str] = Field(default=None, max_length=100)
    serving_size: Optional[str] = Field(default=None, max_length=100, description="e.g. 1 tablet, 30g, 240ml")
    servings_per_container: Optional[float] = Field(default=None)
    storage_instructions: Optional[str] = Field(default=None, max_length=300, description="e.g. Refrigerate after opening, Store below 4°C")
    preparation_instructions: Optional[str] = Field(default=None, max_length=500)
    country_of_origin: Optional[str] = Field(default=None, max_length=100)
    lot_number: Optional[str] = Field(default=None, max_length=100, description="FBA lot-control requirement")

    # Gating & Compliance
    regulatory_approval: Optional[str] = Field(default=None, max_length=300, description="e.g. TFDA Reg No. TZ-FOOD-2024-XXXX")
    is_gated_grocery: bool = Field(default=True, description="Grocery category is restricted; requires compliance proof")

    # Variation theme for grocery: Flavor | Size | Size-Flavor
    # (set on parent Product.variation_theme)

    # Optional
    caffeine_content_mg: Optional[float] = Field(default=None)
    alcohol_content_percent: Optional[float] = Field(default=None)
    is_organic_certified: Optional[bool] = Field(default=False)
    organic_certification_body: Optional[str] = Field(default=None, max_length=200)


# ══════════════════════════════════════════════════════════════════════════════
# 8. TOYS & GAMES
#    Covers: TOY, BOARD_GAME, PUZZLE, OUTDOOR_TOY, VIDEO_GAME
# ══════════════════════════════════════════════════════════════════════════════

class ToyAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_toys"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    minimum_age_years: Optional[float] = Field(default=None, description="Minimum recommended age in years (e.g. 3.0 = 3+)")
    maximum_age_years: Optional[float] = Field(default=None)
    number_of_pieces: Optional[int] = Field(default=None, description="Total piece count")
    material: Optional[str] = Field(default=None, max_length=200)
    batteries_required: Optional[bool] = Field(default=None)

    # Recommended
    batteries_included: Optional[bool] = Field(default=None)
    battery_type: Optional[str] = Field(default=None, max_length=100, description="e.g. AA x 4, CR2032, Rechargeable")
    educational_objective: Optional[str] = Field(default=None, max_length=300, description="e.g. STEM, Creativity, Motor Skills, Language")
    color: Optional[str] = Field(default=None, max_length=100)
    number_of_players: Optional[str] = Field(default=None, max_length=50, description="e.g. 2-6 players")
    play_time_minutes: Optional[int] = Field(default=None, description="Average play time in minutes")
    skill_level: Optional[str] = Field(default=None, max_length=50, description="Beginner, Intermediate, Expert")

    # Safety & Compliance
    safety_certifications: Optional[str] = Field(default=None, max_length=300, description="e.g. CE, ASTM F963, EN 71")
    contains_small_parts: Optional[bool] = Field(default=None)
    is_electric: Optional[bool] = Field(default=None)

    # Video game specific
    platform: Optional[str] = Field(default=None, max_length=100, description="PS5, Xbox Series X, Nintendo Switch, PC")
    esrb_rating: Optional[str] = Field(default=None, max_length=20, description="E, E10+, T, M, AO")
    pegi_rating: Optional[str] = Field(default=None, max_length=10)
    genre: Optional[str] = Field(default=None, max_length=100)


# ══════════════════════════════════════════════════════════════════════════════
# 9. BOOKS & MEDIA
#    Covers: BOOK, MUSIC, MOVIE, DIGITAL_CONTENT
# ══════════════════════════════════════════════════════════════════════════════

class MediaAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_media"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    format: Optional[str] = Field(default=None, max_length=100, description="Hardcover, Paperback, Kindle, Blu-ray, DVD, MP3, FLAC, Streaming")
    language: Optional[str] = Field(default=None, max_length=50)
    publisher: Optional[str] = Field(default=None, max_length=200)
    publication_date: Optional[date] = Field(default=None)

    # Book-specific
    isbn_10: Optional[str] = Field(default=None, max_length=20)
    isbn_13: Optional[str] = Field(default=None, max_length=20)
    author: Optional[str] = Field(default=None, max_length=300, description="Comma-separated for multiple authors")
    number_of_pages: Optional[int] = Field(default=None)
    edition: Optional[str] = Field(default=None, max_length=50)
    genre: Optional[str] = Field(default=None, max_length=100)
    reading_level: Optional[str] = Field(default=None, max_length=50)

    # Music / Movie / Media
    artist: Optional[str] = Field(default=None, max_length=300, description="Artist, director, or creator")
    label: Optional[str] = Field(default=None, max_length=200, description="Record label or studio")
    runtime_minutes: Optional[int] = Field(default=None)
    number_of_discs: Optional[int] = Field(default=None)
    audio_language: Optional[str] = Field(default=None, max_length=100)
    subtitle_language: Optional[str] = Field(default=None, max_length=100)
    content_rating: Optional[str] = Field(default=None, max_length=20, description="G, PG, PG-13, R, TV-MA")
    release_date: Optional[date] = Field(default=None)

    # Optional
    subtitle: Optional[str] = Field(default=None, max_length=300)
    series: Optional[str] = Field(default=None, max_length=200)
    volume_number: Optional[int] = Field(default=None)


# ══════════════════════════════════════════════════════════════════════════════
# 10. AUTOMOTIVE — VEHICLES (CARS)
#     Covers: CAR_NEW, CAR_USED, CAR_CERTIFIED, SUV_NEW, SUV_USED,
#             TRUCK_NEW, TRUCK_USED, VAN_NEW, VAN_USED,
#             ELECTRIC_VEHICLE, HYBRID_VEHICLE, MOTORCYCLE, BUS, MINIBUS
#
#     industry_unique_id on Product = VIN (17-char Vehicle Identification Number)
#     industry_id_type              = "VIN"
# ══════════════════════════════════════════════════════════════════════════════

class AutomotiveVehicleAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_automotive_vehicle"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # ── Core Vehicle Identity ─────────────────────────────────────────────────
    make: Optional[str] = Field(default=None, max_length=100, description="e.g. Toyota, Honda, Mercedes-Benz, Bajaj")
    model: Optional[str] = Field(default=None, max_length=100, description="e.g. Corolla, Civic, C-Class, Boxer")
    year: Optional[int] = Field(default=None, description="Model year e.g. 2022")
    trim: Optional[str] = Field(default=None, max_length=100, description="e.g. Base, Sport, Premium, TRD, AMG")
    body_style: Optional[str] = Field(default=None, max_length=50, description="Sedan, SUV, Hatchback, Pickup, Coupe, Convertible, Wagon, Van, Bus")
    vehicle_type: Optional[str] = Field(default=None, max_length=50, description="Passenger Car, Commercial, Motorcycle, Bus, Minibus, Tractor")

    # ── Engine & Drivetrain ──────────────────────────────────────────────────
    engine_type: Optional[str] = Field(default=None, max_length=100, description="e.g. Petrol, Diesel, Electric, Hybrid, LPG, CNG")
    engine_displacement_cc: Optional[int] = Field(default=None, description="Engine displacement in cc e.g. 1800")
    engine_cylinders: Optional[int] = Field(default=None, description="Number of cylinders e.g. 4, 6, 8")
    horsepower: Optional[int] = Field(default=None, description="Engine output in HP")
    torque_nm: Optional[int] = Field(default=None, description="Engine torque in Nm")
    transmission: Optional[str] = Field(default=None, max_length=50, description="Automatic, Manual, CVT, Semi-Automatic, DCT")
    transmission_speeds: Optional[int] = Field(default=None, description="Number of gears e.g. 6")
    drivetrain: Optional[str] = Field(default=None, max_length=20, description="FWD, RWD, AWD, 4WD, 4x4")
    fuel_type: Optional[str] = Field(default=None, max_length=50, description="Petrol, Diesel, Electric, Hybrid, Plug-in Hybrid, LPG, CNG")
    fuel_tank_capacity_l: Optional[float] = Field(default=None, description="Fuel tank in litres")
    fuel_economy_kmpl: Optional[float] = Field(default=None, description="Fuel economy km/l or combined rating")

    # ── Electric Vehicle Specific ────────────────────────────────────────────
    battery_capacity_kwh: Optional[float] = Field(default=None, description="EV battery capacity in kWh")
    ev_range_km: Optional[int] = Field(default=None, description="Rated electric range in km")
    charging_standard: Optional[str] = Field(default=None, max_length=100, description="e.g. CCS2, CHAdeMO, Type 2, Tesla Supercharger")
    charging_time_hours: Optional[float] = Field(default=None, description="Full charge time in hours (AC)")
    fast_charge_time_minutes: Optional[int] = Field(default=None, description="0–80% DC fast charge time in minutes")

    # ── Exterior ─────────────────────────────────────────────────────────────
    exterior_color: Optional[str] = Field(default=None, max_length=100, description="e.g. Pearl White, Midnight Black, Tungsten Grey")
    exterior_color_code: Optional[str] = Field(default=None, max_length=20, description="Manufacturer paint code")
    number_of_doors: Optional[int] = Field(default=None, description="2, 3, 4, 5")
    roof_type: Optional[str] = Field(default=None, max_length=50, description="Hardtop, Sunroof, Moonroof, Convertible, Panoramic")
    wheel_size_inches: Optional[float] = Field(default=None)
    tire_size: Optional[str] = Field(default=None, max_length=30, description="e.g. 225/55R17")

    # ── Interior ─────────────────────────────────────────────────────────────
    interior_color: Optional[str] = Field(default=None, max_length=100)
    upholstery_material: Optional[str] = Field(default=None, max_length=100, description="Leather, Cloth, Leatherette, Alcantara")
    seating_capacity: Optional[int] = Field(default=None, description="Total number of seats")
    number_of_rows: Optional[int] = Field(default=None, description="1, 2, or 3 rows")
    cargo_volume_l: Optional[float] = Field(default=None, description="Boot/cargo space in litres")

    # ── Safety & Technology ──────────────────────────────────────────────────
    safety_rating: Optional[str] = Field(default=None, max_length=100, description="e.g. NCAP 5-star, NHTSA 4-star")
    airbags: Optional[int] = Field(default=None, description="Number of airbags")
    safety_features: Optional[list] = Field(default=None, sa_column=Column("safety_features", JSON), description="['ABS','ESC','Lane Assist','Blind Spot Monitor','Rear Camera']")
    infotainment_screen_inches: Optional[float] = Field(default=None)
    connectivity_features: Optional[list] = Field(default=None, sa_column=Column("connectivity_features", JSON), description="['Apple CarPlay','Android Auto','Bluetooth','Wi-Fi Hotspot']")
    driver_assistance: Optional[list] = Field(default=None, sa_column=Column("driver_assistance", JSON), description="['Cruise Control','Adaptive Cruise','Parking Sensors','Auto Braking']")

    # ── Vehicle Condition & History (Used / CPO) ─────────────────────────────
    mileage_km: Optional[int] = Field(default=None, description="Odometer reading in km. Required for used vehicles.")
    previous_owners: Optional[int] = Field(default=None, description="Number of previous registered owners")
    accident_history: Optional[bool] = Field(default=None, description="True = has accident record, False = clean history")
    accident_description: Optional[str] = Field(default=None, max_length=500)
    service_history_available: Optional[bool] = Field(default=None)
    last_service_date: Optional[date] = Field(default=None)
    last_service_km: Optional[int] = Field(default=None)
    import_status: Optional[str] = Field(default=None, max_length=50, description="Local, Imported, Duty Paid, Duty Not Paid")
    registration_country: Optional[str] = Field(default=None, max_length=100)
    registration_year: Optional[int] = Field(default=None)
    registration_expiry: Optional[date] = Field(default=None)

    # ── CPO Specific ─────────────────────────────────────────────────────────
    cpo_warranty_months: Optional[int] = Field(default=None, description="Certified Pre-Owned warranty duration in months")
    cpo_warranty_km: Optional[int] = Field(default=None, description="CPO warranty mileage limit")
    cpo_inspection_points: Optional[int] = Field(default=None, description="Number of inspection points checked e.g. 150")
    cpo_dealer: Optional[str] = Field(default=None, max_length=200)

    # ── Pricing & Finance ────────────────────────────────────────────────────
    asking_price_negotiable: Optional[bool] = Field(default=False)
    finance_available: Optional[bool] = Field(default=False)
    minimum_deposit_percent: Optional[float] = Field(default=None)

    # ── OEM / Parts Fitment ──────────────────────────────────────────────────
    oem_part_number: Optional[str] = Field(default=None, max_length=100, description="For vehicle parts listed separately")
    compatible_makes: Optional[list] = Field(default=None, sa_column=Column("compatible_makes", JSON), description="['Toyota','Honda'] — for parts")
    compatible_models: Optional[list] = Field(default=None, sa_column=Column("compatible_models", JSON))
    compatible_years: Optional[list] = Field(default=None, sa_column=Column("compatible_years", JSON), description="[2018, 2019, 2020]")


# ══════════════════════════════════════════════════════════════════════════════
# 11. AUTOMOTIVE — PARTS & ACCESSORIES
#     Covers: AUTO_PART, AUTO_ACCESSORY, TIRE
#
#     industry_unique_id = OEM part number
#     industry_id_type   = "OEM_PART"
# ══════════════════════════════════════════════════════════════════════════════

class AutoPartAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_auto_part"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    oem_part_number: Optional[str] = Field(default=None, max_length=100)
    part_name: Optional[str] = Field(default=None, max_length=200)
    part_category: Optional[str] = Field(default=None, max_length=100, description="e.g. Engine, Brakes, Suspension, Body, Interior, Electrical, Tyres")
    fitment_type: Optional[str] = Field(default=None, max_length=50, description="Direct Fit, Universal, Vehicle-Specific")

    # Fitment Compatibility
    compatible_makes: Optional[list] = Field(default=None, sa_column=Column("compatible_makes", JSON))
    compatible_models: Optional[list] = Field(default=None, sa_column=Column("compatible_models", JSON))
    compatible_years: Optional[list] = Field(default=None, sa_column=Column("compatible_years", JSON))
    compatible_trims: Optional[list] = Field(default=None, sa_column=Column("compatible_trims", JSON))
    compatible_engine_types: Optional[list] = Field(default=None, sa_column=Column("compatible_engine_types", JSON))

    # Tire-specific
    tire_width_mm: Optional[int] = Field(default=None)
    tire_aspect_ratio: Optional[int] = Field(default=None)
    rim_diameter_inches: Optional[float] = Field(default=None)
    tire_season: Optional[str] = Field(default=None, max_length=20, description="All-Season, Summer, Winter, All-Terrain")
    load_index: Optional[int] = Field(default=None)
    speed_rating: Optional[str] = Field(default=None, max_length=5, description="e.g. H, V, W, Y")

    # Optional
    warranty_months: Optional[int] = Field(default=None)
    material: Optional[str] = Field(default=None, max_length=100)
    country_of_origin: Optional[str] = Field(default=None, max_length=100)
    is_oem: Optional[bool] = Field(default=None, description="True = genuine OEM, False = aftermarket")


# ══════════════════════════════════════════════════════════════════════════════
# 12. JEWELRY & WATCHES
#     Covers: JEWELRY, WATCH
# ══════════════════════════════════════════════════════════════════════════════

class JewelryWatchAttributes(SQLModel, table=True):
    __tablename__ = "product_attrs_jewelry_watch"

    product_id: UUID = Field(primary_key=True, foreign_key="products.product_id")

    # Required
    material: Optional[str] = Field(default=None, max_length=200, description="e.g. 18K Gold, 925 Sterling Silver, Stainless Steel, Platinum")
    color: Optional[str] = Field(default=None, max_length=100, description="Gold, Rose Gold, Silver, Black")
    gemstone: Optional[str] = Field(default=None, max_length=200, description="e.g. Diamond, Ruby, Sapphire, None")
    gender: Optional[str] = Field(default=None, max_length=50, description="Men, Women, Unisex, Boys, Girls")

    # Jewelry-specific
    ring_size: Optional[str] = Field(default=None, max_length=20, description="US ring size e.g. 7, or diameter in mm")
    chain_length_cm: Optional[float] = Field(default=None)
    clasp_type: Optional[str] = Field(default=None, max_length=50, description="Lobster, Spring Ring, Toggle, Magnetic")
    setting_type: Optional[str] = Field(default=None, max_length=50, description="Prong, Bezel, Pave, Channel, Tension")
    carat_weight: Optional[float] = Field(default=None, description="Total carat weight of gemstones")
    metal_purity: Optional[str] = Field(default=None, max_length=20, description="e.g. 18K, 24K, 925, 950")

    # Watch-specific
    watch_movement: Optional[str] = Field(default=None, max_length=50, description="Quartz, Automatic, Manual, Solar, Smartwatch")
    case_diameter_mm: Optional[float] = Field(default=None)
    case_thickness_mm: Optional[float] = Field(default=None)
    band_material: Optional[str] = Field(default=None, max_length=100, description="Leather, Stainless Steel, Silicone, NATO, Rubber")
    band_width_mm: Optional[float] = Field(default=None)
    water_resistance_atm: Optional[int] = Field(default=None, description="Water resistance in ATM e.g. 5 ATM = 50m")
    display_type: Optional[str] = Field(default=None, max_length=30, description="Analog, Digital, Ana-Digi")
    complications: Optional[list] = Field(default=None, sa_column=Column("complications", JSON), description="['Chronograph','Date','GMT','Moonphase','Tourbillon']")
    crystal_type: Optional[str] = Field(default=None, max_length=50, description="Sapphire, Mineral, Acrylic")
    warranty_months: Optional[int] = Field(default=None)
