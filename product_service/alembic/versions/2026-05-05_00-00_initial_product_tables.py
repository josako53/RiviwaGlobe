"""initial_product_tables

Revision ID: a1f2e3d4c5b6
Revises:
Create Date: 2026-05-05 00:00:00.000000+00:00

Creates all product_service tables:
  - org_cache
  - products
  - product_bullet_points
  - product_images
  - product_attributes
  - product_attrs_electronics
  - product_attrs_apparel
  - product_attrs_footwear
  - product_attrs_home_kitchen
  - product_attrs_bedding
  - product_attrs_health
  - product_attrs_food_beverage
  - product_attrs_toys
  - product_attrs_media
  - product_attrs_automotive_vehicle
  - product_attrs_auto_part
  - product_attrs_jewelry_watch
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1f2e3d4c5b6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── org_cache ─────────────────────────────────────────────────────────────
    op.create_table(
        "org_cache",
        sa.Column("org_id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("slug", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
    )

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("product_id", sa.UUID(), primary_key=True),
        sa.Column("rsin", sa.String(10), nullable=True, unique=True),
        sa.Column("seller_sku", sa.String(100), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("upc", sa.String(20), nullable=True),
        sa.Column("ean", sa.String(20), nullable=True),
        sa.Column("gtin", sa.String(20), nullable=True),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("mpn", sa.String(100), nullable=True),
        sa.Column("industry_unique_id", sa.String(100), nullable=True),
        sa.Column("industry_id_type", sa.String(50), nullable=True),
        sa.Column("product_type", sa.String(50), nullable=False),
        sa.Column("browse_node_id", sa.String(50), nullable=True),
        sa.Column("browse_node_path", sa.String(500), nullable=True),
        sa.Column("item_type_keyword", sa.String(200), nullable=True),
        sa.Column("product_supervisor", sa.String(200), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("brand", sa.String(200), nullable=False),
        sa.Column("manufacturer", sa.String(200), nullable=True),
        sa.Column("model_number", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("usage", sa.Text(), nullable=True),
        sa.Column("production_location", sa.String(300), nullable=True),
        sa.Column("country_of_origin", sa.String(100), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="TZS"),
        sa.Column("condition", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fulfillment_method", sa.String(20), nullable=False, server_default="MERCHANT"),
        sa.Column("fulfillment_center_shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("item_weight", sa.Float(), nullable=True),
        sa.Column("item_weight_unit", sa.String(10), nullable=False, server_default="kg"),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("dimensions_unit", sa.String(10), nullable=False, server_default="cm"),
        sa.Column("main_image_url", sa.String(1000), nullable=True),
        sa.Column("is_parent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parent_product_id", sa.UUID(), nullable=True),
        sa.Column("variation_theme", sa.String(30), nullable=True),
        sa.Column("variation_values", sa.JSON(), nullable=True),
        sa.Column("listing_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_gated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("suppression_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organisation_id", "seller_sku", name="uq_org_sku"),
    )
    op.create_index("ix_products_rsin", "products", ["rsin"])
    op.create_index("ix_products_organisation_id", "products", ["organisation_id"])
    op.create_index("ix_products_product_type", "products", ["product_type"])
    op.create_index("ix_products_listing_status", "products", ["listing_status"])
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_index("ix_products_industry_unique_id", "products", ["industry_unique_id"])
    op.create_index("ix_products_parent_product_id", "products", ["parent_product_id"])

    # ── product_bullet_points ─────────────────────────────────────────────────
    op.create_table(
        "product_bullet_points",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
    )
    op.create_index("ix_product_bullet_points_product_id", "product_bullet_points", ["product_id"])

    # ── product_images ────────────────────────────────────────────────────────
    op.create_table(
        "product_images",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="ALTERNATE"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("alt_text", sa.String(200), nullable=True),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    # ── product_attributes ────────────────────────────────────────────────────
    op.create_table(
        "product_attributes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attribute_name", sa.String(200), nullable=False),
        sa.Column("attribute_value", sa.String(1000), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("group", sa.String(100), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_product_attributes_product_id", "product_attributes", ["product_id"])

    # ── Category attribute tables (all share the same FK pattern) ─────────────

    def _cat_table(name: str, *cols):
        op.create_table(
            name,
            sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True),
            *cols,
        )

    _cat_table("product_attrs_electronics",
        sa.Column("processor_brand", sa.String(100)), sa.Column("processor_model", sa.String(100)),
        sa.Column("ram_gb", sa.Integer()), sa.Column("storage_gb", sa.Integer()),
        sa.Column("storage_type", sa.String(50)), sa.Column("display_size_inches", sa.Float()),
        sa.Column("display_resolution", sa.String(50)), sa.Column("display_type", sa.String(50)),
        sa.Column("operating_system", sa.String(100)), sa.Column("connectivity", sa.String(200)),
        sa.Column("battery_life_hours", sa.Float()), sa.Column("battery_capacity_mah", sa.Integer()),
        sa.Column("color", sa.String(100)), sa.Column("ports", sa.String(300)),
        sa.Column("graphics_card", sa.String(100)), sa.Column("refresh_rate_hz", sa.Integer()),
        sa.Column("camera_mp", sa.Float()), sa.Column("water_resistance_rating", sa.String(20)),
        sa.Column("form_factor", sa.String(50)), sa.Column("compatible_devices", sa.String(300)),
        sa.Column("included_accessories", sa.String(300)), sa.Column("voltage", sa.String(20)),
        sa.Column("wattage", sa.Float()), sa.Column("special_features", sa.String(300)),
    )

    _cat_table("product_attrs_apparel",
        sa.Column("size", sa.String(50)), sa.Column("color", sa.String(100)),
        sa.Column("department", sa.String(50)), sa.Column("material", sa.String(200)),
        sa.Column("closure_type", sa.String(100)), sa.Column("fabric_type", sa.String(100)),
        sa.Column("care_instructions", sa.String(300)), sa.Column("fit_type", sa.String(50)),
        sa.Column("neckline", sa.String(50)), sa.Column("sleeve_type", sa.String(50)),
        sa.Column("pattern", sa.String(100)), sa.Column("occasion", sa.String(100)),
        sa.Column("size_system", sa.String(20)), sa.Column("chest_cm", sa.Float()),
        sa.Column("waist_cm", sa.Float()), sa.Column("hip_cm", sa.Float()),
        sa.Column("inseam_cm", sa.Float()), sa.Column("length_cm", sa.Float()),
        sa.Column("country_size_map", sa.JSON()),
    )

    _cat_table("product_attrs_footwear",
        sa.Column("shoe_size", sa.String(20)), sa.Column("shoe_size_system", sa.String(20)),
        sa.Column("shoe_width", sa.String(20)), sa.Column("color", sa.String(100)),
        sa.Column("outer_material", sa.String(100)), sa.Column("sole_material", sa.String(100)),
        sa.Column("closure_type", sa.String(100)), sa.Column("target_gender", sa.String(50)),
        sa.Column("heel_height_cm", sa.Float()), sa.Column("heel_type", sa.String(50)),
        sa.Column("toe_shape", sa.String(50)), sa.Column("lining_material", sa.String(100)),
        sa.Column("waterproof", sa.Boolean()), sa.Column("occasion", sa.String(100)),
        sa.Column("platform_height_cm", sa.Float()), sa.Column("shaft_height_cm", sa.Float()),
    )

    _cat_table("product_attrs_home_kitchen",
        sa.Column("material", sa.String(200)), sa.Column("color", sa.String(100)),
        sa.Column("item_count", sa.Integer()), sa.Column("capacity_ml", sa.Float()),
        sa.Column("capacity_unit", sa.String(20)), sa.Column("dishwasher_safe", sa.Boolean()),
        sa.Column("microwave_safe", sa.Boolean()), sa.Column("oven_safe", sa.Boolean()),
        sa.Column("oven_safe_temp_celsius", sa.Integer()),
        sa.Column("compatible_stove_types", sa.String(200)),
        sa.Column("finish_type", sa.String(100)), sa.Column("assembly_required", sa.Boolean()),
        sa.Column("number_of_shelves", sa.Integer()), sa.Column("weight_capacity_kg", sa.Float()),
        sa.Column("wattage", sa.Float()), sa.Column("voltage", sa.String(20)),
        sa.Column("included_components", sa.String(300)), sa.Column("style", sa.String(100)),
    )

    _cat_table("product_attrs_bedding",
        sa.Column("size", sa.String(50)), sa.Column("color", sa.String(100)),
        sa.Column("fill_material", sa.String(100)), sa.Column("item_count", sa.Integer()),
        sa.Column("care_instructions", sa.String(300)), sa.Column("thread_count", sa.Integer()),
        sa.Column("material", sa.String(200)), sa.Column("fill_power", sa.Integer()),
        sa.Column("firmness", sa.String(50)), sa.Column("mattress_type", sa.String(100)),
        sa.Column("mattress_depth_cm", sa.Float()), sa.Column("pattern", sa.String(100)),
        sa.Column("hypoallergenic", sa.Boolean()), sa.Column("cooling_technology", sa.String(100)),
    )

    _cat_table("product_attrs_health",
        sa.Column("active_ingredients", sa.JSON()), sa.Column("dosage_form", sa.String(100)),
        sa.Column("item_count", sa.Integer()), sa.Column("directions", sa.String(1000)),
        sa.Column("warnings", sa.String(1000)), sa.Column("age_range", sa.String(50)),
        sa.Column("drug_facts", sa.JSON()), sa.Column("inactive_ingredients", sa.String(500)),
        sa.Column("allergen_information", sa.String(300)),
        sa.Column("storage_instructions", sa.String(300)),
        sa.Column("expiration_date", sa.Date()), sa.Column("lot_number", sa.String(100)),
        sa.Column("regulatory_approval", sa.String(200)),
        sa.Column("is_prescription_required", sa.Boolean(), server_default="false"),
        sa.Column("flavor", sa.String(100)), sa.Column("unit_count", sa.Float()),
        sa.Column("unit_count_type", sa.String(30)),
    )

    _cat_table("product_attrs_food_beverage",
        sa.Column("is_expirable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expiration_date", sa.Date()),
        sa.Column("fulfillment_center_shelf_life_days", sa.Integer()),
        sa.Column("ingredients", sa.JSON()), sa.Column("nutrition_facts", sa.JSON()),
        sa.Column("allergen_information", sa.String(500)),
        sa.Column("dietary_claims", sa.JSON()),
        sa.Column("item_package_quantity", sa.Integer()),
        sa.Column("unit_count", sa.Float()), sa.Column("unit_count_type", sa.String(20)),
        sa.Column("price_per_unit", sa.String(50)), sa.Column("flavor", sa.String(100)),
        sa.Column("serving_size", sa.String(100)), sa.Column("servings_per_container", sa.Float()),
        sa.Column("storage_instructions", sa.String(300)),
        sa.Column("preparation_instructions", sa.String(500)),
        sa.Column("country_of_origin", sa.String(100)), sa.Column("lot_number", sa.String(100)),
        sa.Column("regulatory_approval", sa.String(300)),
        sa.Column("is_gated_grocery", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("caffeine_content_mg", sa.Float()), sa.Column("alcohol_content_percent", sa.Float()),
        sa.Column("is_organic_certified", sa.Boolean(), server_default="false"),
        sa.Column("organic_certification_body", sa.String(200)),
    )

    _cat_table("product_attrs_toys",
        sa.Column("minimum_age_years", sa.Float()), sa.Column("maximum_age_years", sa.Float()),
        sa.Column("number_of_pieces", sa.Integer()), sa.Column("material", sa.String(200)),
        sa.Column("batteries_required", sa.Boolean()), sa.Column("batteries_included", sa.Boolean()),
        sa.Column("battery_type", sa.String(100)),
        sa.Column("educational_objective", sa.String(300)),
        sa.Column("color", sa.String(100)), sa.Column("number_of_players", sa.String(50)),
        sa.Column("play_time_minutes", sa.Integer()), sa.Column("skill_level", sa.String(50)),
        sa.Column("safety_certifications", sa.String(300)),
        sa.Column("contains_small_parts", sa.Boolean()), sa.Column("is_electric", sa.Boolean()),
        sa.Column("platform", sa.String(100)), sa.Column("esrb_rating", sa.String(20)),
        sa.Column("pegi_rating", sa.String(10)), sa.Column("genre", sa.String(100)),
    )

    _cat_table("product_attrs_media",
        sa.Column("format", sa.String(100)), sa.Column("language", sa.String(50)),
        sa.Column("publisher", sa.String(200)), sa.Column("publication_date", sa.Date()),
        sa.Column("isbn_10", sa.String(20)), sa.Column("isbn_13", sa.String(20)),
        sa.Column("author", sa.String(300)), sa.Column("number_of_pages", sa.Integer()),
        sa.Column("edition", sa.String(50)), sa.Column("genre", sa.String(100)),
        sa.Column("reading_level", sa.String(50)), sa.Column("artist", sa.String(300)),
        sa.Column("label", sa.String(200)), sa.Column("runtime_minutes", sa.Integer()),
        sa.Column("number_of_discs", sa.Integer()), sa.Column("audio_language", sa.String(100)),
        sa.Column("subtitle_language", sa.String(100)),
        sa.Column("content_rating", sa.String(20)), sa.Column("release_date", sa.Date()),
        sa.Column("subtitle", sa.String(300)), sa.Column("series", sa.String(200)),
        sa.Column("volume_number", sa.Integer()),
    )

    _cat_table("product_attrs_automotive_vehicle",
        sa.Column("make", sa.String(100)), sa.Column("model", sa.String(100)),
        sa.Column("year", sa.Integer()), sa.Column("trim", sa.String(100)),
        sa.Column("body_style", sa.String(50)), sa.Column("vehicle_type", sa.String(50)),
        sa.Column("engine_type", sa.String(100)),
        sa.Column("engine_displacement_cc", sa.Integer()),
        sa.Column("engine_cylinders", sa.Integer()), sa.Column("horsepower", sa.Integer()),
        sa.Column("torque_nm", sa.Integer()), sa.Column("transmission", sa.String(50)),
        sa.Column("transmission_speeds", sa.Integer()), sa.Column("drivetrain", sa.String(20)),
        sa.Column("fuel_type", sa.String(50)),
        sa.Column("fuel_tank_capacity_l", sa.Float()),
        sa.Column("fuel_economy_kmpl", sa.Float()),
        sa.Column("battery_capacity_kwh", sa.Float()), sa.Column("ev_range_km", sa.Integer()),
        sa.Column("charging_standard", sa.String(100)),
        sa.Column("charging_time_hours", sa.Float()),
        sa.Column("fast_charge_time_minutes", sa.Integer()),
        sa.Column("exterior_color", sa.String(100)),
        sa.Column("exterior_color_code", sa.String(20)),
        sa.Column("number_of_doors", sa.Integer()), sa.Column("roof_type", sa.String(50)),
        sa.Column("wheel_size_inches", sa.Float()), sa.Column("tire_size", sa.String(30)),
        sa.Column("interior_color", sa.String(100)),
        sa.Column("upholstery_material", sa.String(100)),
        sa.Column("seating_capacity", sa.Integer()), sa.Column("number_of_rows", sa.Integer()),
        sa.Column("cargo_volume_l", sa.Float()), sa.Column("safety_rating", sa.String(100)),
        sa.Column("airbags", sa.Integer()), sa.Column("safety_features", sa.JSON()),
        sa.Column("infotainment_screen_inches", sa.Float()),
        sa.Column("connectivity_features", sa.JSON()),
        sa.Column("driver_assistance", sa.JSON()),
        sa.Column("mileage_km", sa.Integer()),
        sa.Column("previous_owners", sa.Integer()),
        sa.Column("accident_history", sa.Boolean()),
        sa.Column("accident_description", sa.String(500)),
        sa.Column("service_history_available", sa.Boolean()),
        sa.Column("last_service_date", sa.Date()), sa.Column("last_service_km", sa.Integer()),
        sa.Column("import_status", sa.String(50)),
        sa.Column("registration_country", sa.String(100)),
        sa.Column("registration_year", sa.Integer()),
        sa.Column("registration_expiry", sa.Date()),
        sa.Column("cpo_warranty_months", sa.Integer()),
        sa.Column("cpo_warranty_km", sa.Integer()),
        sa.Column("cpo_inspection_points", sa.Integer()),
        sa.Column("cpo_dealer", sa.String(200)),
        sa.Column("asking_price_negotiable", sa.Boolean(), server_default="false"),
        sa.Column("finance_available", sa.Boolean(), server_default="false"),
        sa.Column("minimum_deposit_percent", sa.Float()),
        sa.Column("oem_part_number", sa.String(100)),
        sa.Column("compatible_makes", sa.JSON()), sa.Column("compatible_models", sa.JSON()),
        sa.Column("compatible_years", sa.JSON()),
    )

    _cat_table("product_attrs_auto_part",
        sa.Column("oem_part_number", sa.String(100)), sa.Column("part_name", sa.String(200)),
        sa.Column("part_category", sa.String(100)), sa.Column("fitment_type", sa.String(50)),
        sa.Column("compatible_makes", sa.JSON()), sa.Column("compatible_models", sa.JSON()),
        sa.Column("compatible_years", sa.JSON()), sa.Column("compatible_trims", sa.JSON()),
        sa.Column("compatible_engine_types", sa.JSON()),
        sa.Column("tire_width_mm", sa.Integer()), sa.Column("tire_aspect_ratio", sa.Integer()),
        sa.Column("rim_diameter_inches", sa.Float()), sa.Column("tire_season", sa.String(20)),
        sa.Column("load_index", sa.Integer()), sa.Column("speed_rating", sa.String(5)),
        sa.Column("warranty_months", sa.Integer()), sa.Column("material", sa.String(100)),
        sa.Column("country_of_origin", sa.String(100)), sa.Column("is_oem", sa.Boolean()),
    )

    _cat_table("product_attrs_jewelry_watch",
        sa.Column("material", sa.String(200)), sa.Column("color", sa.String(100)),
        sa.Column("gemstone", sa.String(200)), sa.Column("gender", sa.String(50)),
        sa.Column("ring_size", sa.String(20)), sa.Column("chain_length_cm", sa.Float()),
        sa.Column("clasp_type", sa.String(50)), sa.Column("setting_type", sa.String(50)),
        sa.Column("carat_weight", sa.Float()), sa.Column("metal_purity", sa.String(20)),
        sa.Column("watch_movement", sa.String(50)), sa.Column("case_diameter_mm", sa.Float()),
        sa.Column("case_thickness_mm", sa.Float()), sa.Column("band_material", sa.String(100)),
        sa.Column("band_width_mm", sa.Float()), sa.Column("water_resistance_atm", sa.Integer()),
        sa.Column("display_type", sa.String(30)), sa.Column("complications", sa.JSON()),
        sa.Column("crystal_type", sa.String(50)), sa.Column("warranty_months", sa.Integer()),
    )


def downgrade() -> None:
    for tbl in [
        "product_attrs_jewelry_watch", "product_attrs_auto_part",
        "product_attrs_automotive_vehicle", "product_attrs_media",
        "product_attrs_toys", "product_attrs_food_beverage",
        "product_attrs_health", "product_attrs_bedding",
        "product_attrs_home_kitchen", "product_attrs_footwear",
        "product_attrs_apparel", "product_attrs_electronics",
        "product_attributes", "product_images",
        "product_bullet_points", "products", "org_cache",
    ]:
        op.drop_table(tbl)
