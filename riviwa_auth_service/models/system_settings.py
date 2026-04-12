# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  models/system_settings.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/system_settings.py
────────────────────────────────────────────────────────────────────────────
Single-row platform configuration table.

Design: one row, always present (seeded by the startup seed function).
The row is fetched by a fixed PRIMARY KEY of 1 — there is only ever one
platform, so a compound key or slug key adds no value.

Fields exposed via /admin/system/ endpoints:
  logo_url        — full public URL to the app/platform logo in MinIO
  logo_updated_at — when the logo was last changed (for cache-busting)
  logo_updated_by — which super_admin changed it
  app_name        — e.g. "Riviwa GRM"  (shown in emails, browser title)
  support_email   — shown in notification templates
  support_phone   — shown in notification templates
  primary_color   — hex colour used by white-label clients (#185FA5)
  secondary_color — hex colour

Extend this table (via Alembic migration) as the platform needs more
global settings — never add platform-wide config to .env when it needs
to be changeable at runtime without a redeploy.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, Field, SQLModel
from sqlalchemy import DateTime, Integer, String, text


class SystemSettings(SQLModel, table=True):
    __tablename__ = "system_settings"

    # Fixed PK — always 1.  Never create a second row.
    id: int = Field(
        default=1,
        sa_column=Column(Integer, primary_key=True),
        description="Always 1 — single-row table.",
    )

    # ── Branding ──────────────────────────────────────────────────────────────
    app_name: str = Field(
        default="Riviwa GRM",
        max_length=128,
        description="Platform display name shown in emails and the browser title.",
    )
    logo_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Full public URL to the platform logo stored in MinIO.",
    )
    logo_updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the logo was last uploaded.",
    )
    logo_updated_by: Optional[uuid.UUID] = Field(
        default=None,
        description="user.id of the super_admin who last changed the logo.",
    )
    favicon_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description="URL to the platform favicon (16×16 or 32×32 ICO/PNG).",
    )

    # ── Contact ───────────────────────────────────────────────────────────────
    support_email: Optional[str] = Field(
        default="support@riviwa.com",
        max_length=255,
        description="Support email shown in notification templates and error pages.",
    )
    support_phone: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Support phone number shown in notification templates.",
    )

    # ── Theme colours ─────────────────────────────────────────────────────────
    primary_color: str = Field(
        default="#185FA5",
        max_length=7,
        description="Primary brand colour (hex, e.g. #185FA5).",
    )
    secondary_color: str = Field(
        default="#1D9E75",
        max_length=7,
        description="Secondary brand colour (hex).",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
    )
