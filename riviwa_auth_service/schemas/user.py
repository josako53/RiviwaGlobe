"""
schemas/user.py
═══════════════════════════════════════════════════════════════════════════════
Read and write schemas for the User resource.

Follows the "schema trinity" pattern:
  UserPublicResponse   → safe subset for public-facing API responses
                         (e.g. shown to other users in marketplace contexts)
  UserPrivateResponse  → full profile returned to the authenticated user
                         (GET /api/v1/users/me)
  UserUpdateRequest    → fields the user can change themselves
                         (PATCH /api/v1/users/me)
  UserAvatarUpdateRequest → avatar URL update

All schemas are READ-ONLY for fields managed by the server (id, status,
created_at, etc.).  The user can only update the fields defined in
UserUpdateRequest.

Field mapping:  all fields mirror columns on the User model (user.py).
               See models/user.py for authoritative descriptions.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from schemas.common import validate_e164, validate_username


# ─────────────────────────────────────────────────────────────────────────────
# Public profile  (visible to other authenticated users)
# ─────────────────────────────────────────────────────────────────────────────

class UserPublicResponse(BaseModel):
    """
    Minimal user profile safe for public display.

    Returned in contexts where another user or an anonymous party needs
    to see basic identity info — e.g. a service listing page showing
    the seller's profile, or an org member directory.

    Sensitive fields (email, phone, hashed_password, security flags) are
    intentionally excluded.
    """
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:           uuid.UUID    = Field(description="User's unique identifier.")
    username:     str          = Field(description="Public handle.")
    display_name: Optional[str] = Field(default=None, description="Preferred display name.")
    avatar_url:   Optional[str] = Field(default=None, description="Profile picture URL.")
    is_verified:  bool          = Field(
        alias="id_verified",
        description="True when government ID verification has been approved.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Private profile  (returned only to the authenticated user themselves)
# ─────────────────────────────────────────────────────────────────────────────

class UserPrivateResponse(BaseModel):
    """
    Full user profile returned to GET /api/v1/users/me.

    Includes all non-secret fields that the user needs to manage their account.
    Excludes: hashed_password, two_factor_secret, internal fraud fields.

    Maps directly to the User model.  Field names match model column names
    except where noted.
    """
    model_config = ConfigDict(from_attributes=True, frozen=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    id:               uuid.UUID     = Field(description="Primary key.")
    username:         str           = Field()
    email:            Optional[str] = Field(default=None, description="Registered email address. Null for phone-only accounts.")
    phone_number:     Optional[str] = Field(default=None, description="E.164 phone number.")

    # ── Verification flags ────────────────────────────────────────────────────
    is_email_verified: bool = Field()
    phone_verified:    bool = Field()
    id_verified:       bool = Field(description="Government ID verified.")

    # ── Profile ───────────────────────────────────────────────────────────────
    display_name: Optional[str] = Field(default=None)
    full_name:    Optional[str] = Field(default=None)
    avatar_url:   Optional[str] = Field(default=None)
    date_of_birth: Optional[str] = Field(
        default=None,
        description="ISO-8601 date string (YYYY-MM-DD).",
    )
    gender:       Optional[str] = Field(default=None)
    country_code: Optional[str] = Field(default=None, description="ISO-3166-1 alpha-2.")
    language:     str           = Field(default="en", description="BCP-47 language tag.")

    # ── Account status ────────────────────────────────────────────────────────
    status: str = Field(description="Account lifecycle status (AccountStatus enum value).")

    # ── OAuth ─────────────────────────────────────────────────────────────────
    oauth_provider:    Optional[str] = Field(default=None, description="'google' | 'apple' | 'facebook' | null.")
    has_password:      bool          = Field(
        description="True when hashed_password is set. False for social-only accounts.",
    )

    # ── Security ──────────────────────────────────────────────────────────────
    two_factor_enabled: bool = Field(description="Whether 2FA / OTP login is enabled.")

    # ── Dashboard context ─────────────────────────────────────────────────────
    active_org_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Currently active org dashboard UUID, or null for personal view.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at:    datetime           = Field()
    updated_at:    datetime           = Field()
    last_login_at: Optional[datetime] = Field(default=None)


# ─────────────────────────────────────────────────────────────────────────────
# Update request  (PATCH /api/v1/users/me)
# ─────────────────────────────────────────────────────────────────────────────

class UserUpdateRequest(BaseModel):
    """
    Fields the authenticated user can update on their own profile.

    All fields are optional — only supplied fields are updated (PATCH semantics).
    Empty strings are rejected; pass null to clear a nullable field.

    Fields NOT changeable here (handled by dedicated endpoints):
      · email       → POST /api/v1/users/me/change-email  (triggers OTP)
      · phone_number → POST /api/v1/users/me/change-phone  (triggers OTP)
      · password    → POST /api/v1/auth/password/change
      · avatar_url  → POST /api/v1/users/me/avatar
      · status      → admin-only
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="New username. Must be unique. 3–50 chars, letters/digits/._-",
    )
    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Preferred display name (shown in UI).",
    )
    full_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Full legal name.",
    )
    date_of_birth: Optional[str] = Field(
        default=None,
        description="ISO-8601 date string (YYYY-MM-DD). e.g. '1990-07-15'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    gender: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Gender identity (free-text; platform does not restrict values).",
    )
    country_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="ISO-3166-1 alpha-2 country code. e.g. 'US', 'TZ', 'IT'.",
        pattern=r"^[A-Z]{2}$",
    )
    language: Optional[str] = Field(
        default=None,
        max_length=10,
        description="BCP-47 language tag. e.g. 'en', 'sw', 'fr', 'it'.",
    )

    @model_validator(mode="after")
    def _validate_fields(self) -> "UserUpdateRequest":
        if self.username is not None:
            self.username = validate_username(self.username)
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Avatar update  (POST /api/v1/users/me/avatar)
# ─────────────────────────────────────────────────────────────────────────────

class UserAvatarUpdateRequest(BaseModel):
    """
    Set or clear the user's avatar URL.

    `avatar_url` must be an HTTPS URL pointing to an already-uploaded image.
    The upload itself is handled separately (e.g. via a pre-signed S3 URL).
    Pass null to clear the avatar (revert to default/initials avatar).
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    avatar_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description="HTTPS URL of the uploaded avatar image, or null to clear.",
        examples=["https://cdn.riviwa.com/avatars/user-uuid.jpg"],
    )

    @model_validator(mode="after")
    def _validate_url(self) -> "UserAvatarUpdateRequest":
        if self.avatar_url is not None:
            if not self.avatar_url.startswith("https://"):
                raise ValueError("avatar_url must be a secure HTTPS URL.")
        return self