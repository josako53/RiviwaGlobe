"""
schemas/fraud.py
═══════════════════════════════════════════════════════════════════════════════
Pydantic v2 request / response schemas for the fraud-detection and
three-step registration subsystems.

Three-step registration flow
────────────────────────────
  Step 1  POST /register/initiate
          Request:  RegistrationInitiateRequest
          Response: RegistrationInitiateResponse
            action: "verify_email" | "verify_phone"
            session_token → stored in Redis as reg_otp:<token>

  Step 2  POST /register/verify-otp
          Request:  OTPVerifyRequest
          Response: OTPVerifyResponse
            action: "set_password"
            continuation_token → stored in Redis as reg_cont:<token>

  Step 3  POST /register/complete
          Request:  RegistrationCompleteRequest
          Response: RegistrationResponse
            action: "complete" | "id_verification_pending"

  Resend  POST /register/resend-otp
          Request:  OTPResendRequest
          Response: RegistrationInitiateResponse  (new session_token)

Fraud signals  (POSTed by fraud-collector.js before form submission)
─────────────────────────────────────────────────────────────────────
  POST /register/fingerprint  →  FingerprintPayload
  POST /register/behavioral   →  BehavioralSummary
  Both carry the same session_token to link signals together.

ID verification webhook  (called by Stripe / Onfido / stub)
────────────────────────────────────────────────────────────
  POST /register/webhook/id-verify  →  IDVerificationWebhook
  Normalised internal DTO — never exposed to clients.

Legacy single-step endpoint  (backward-compat)
───────────────────────────────────────────────
  POST /register  →  RegistrationRequest / RegistrationResponse

Cross-check guarantees maintained by this file
───────────────────────────────────────────────
  FingerprintPayload
    .model_dump(exclude={"session_token"}) produces a dict whose keys are
    an exact subset of DeviceFingerprint column names.  Unpacking it directly
    into DeviceFingerprint(**data) via FraudRepository.upsert_fingerprint()
    will never raise an unexpected-keyword-argument error.

  BehavioralSummary
    .model_dump(exclude={"session_token"}) produces a dict whose keys are an
    exact subset of the writable BehavioralSession columns.  Passing **fields
    into FraudRepository.update_behavioral_session() will never raise
    AttributeError.  Read-only columns (ml_bot_probability, behavioral_score,
    id, created_at, scored_at) are intentionally absent from this schema.

  IDVerificationWebhook
    Contains every field accessed by IDVerificationService._handle_approved()
    and _handle_rejected(): provider_session_id, status, id_number_hash,
    id_type, id_country, name_match, dob_match, rejection_reason, raw_payload.

  OTPVerifyResponse
    Uses continuation_token (not verified_session_token) to match the field
    name that registration_service.verify_otp() stores in Redis under the
    reg_cont: prefix.

  Class ordering
    FingerprintPayload and BehavioralSummary are declared BEFORE the request
    classes that reference them, so no forward-reference NameError can occur
    regardless of whether from __future__ import annotations is active.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Shared validator
# ─────────────────────────────────────────────────────────────────────────────

# Stricter than the previous inline check:
#   + must start with +
#   + first digit after + must be 1-9  (no +0...)
#   + total length 8-16 chars  (ITU E.164: max 15 digits + leading +)
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def _validate_e164(value: Optional[str]) -> Optional[str]:
    """Return stripped E.164 string or raise ValueError."""
    if value is None:
        return None
    v = value.strip()
    if not _E164_RE.match(v):
        raise ValueError(
            "Phone number must be in E.164 format, e.g. +12125551234 "
            "('+' followed by 8–15 digits, first digit non-zero)."
        )
    return v


# ─────────────────────────────────────────────────────────────────────────────
# FingerprintPayload
# ─────────────────────────────────────────────────────────────────────────────

class FingerprintPayload(BaseModel):
    """
    Browser device fingerprint collected by fraud-collector.js.

    POSTed to  POST /register/fingerprint  on page load, before the user
    submits the form.  The session_token links this record to BehavioralSummary
    and ultimately to the User row created in Step 1.

    DB contract
    ───────────
    .model_dump(exclude={"session_token"}) is unpacked directly into
    FraudRepository.upsert_fingerprint(user_id, data) which constructs
    DeviceFingerprint(user_id=user_id, **data).

    Every key in the resulting dict MUST be a column on DeviceFingerprint.
    The following columns are intentionally absent because they are managed
    by the ORM, not by the caller:
        id, user_id, first_seen, last_seen, seen_count

    Used by
    ───────
    • api/v1/endpoints/registration.py  — request body type
    • services/fraud_scoring.py          — ScoringInput.fingerprint field;
        accesses: fingerprint_hash, webdriver_detected,
                  headless_detected, inconsistencies_count
    • services/registration_service.py  — .fingerprint_hash lookup,
        .model_dump(exclude={"session_token"}) → upsert_fingerprint()
    """

    # ── Linking token (excluded from DB insert) ───────────────────────────────
    session_token: str = Field(
        ...,
        min_length=10,
        max_length=64,
        description=(
            "Opaque token issued on page load by fraud-collector.js. "
            "Links this fingerprint record to the BehavioralSummary and to "
            "the in-progress registration session."
        ),
    )

    # ── Composite hash (primary duplicate-detection key) ─────────────────────
    fingerprint_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description=(
            "SHA-256 hex digest of the composite browser fingerprint "
            "(canvas + audio + WebGL + fonts + screen + timezone + UA). "
            "Primary key for duplicate-device detection."
        ),
    )

    # ── Component hashes (optional — best-effort collection by JS) ───────────
    canvas_hash: Optional[str] = Field(default=None, max_length=64)
    audio_hash:  Optional[str] = Field(default=None, max_length=64)
    webgl_hash:  Optional[str] = Field(default=None, max_length=64)
    fonts_hash:  Optional[str] = Field(default=None, max_length=64)
    screen_hash: Optional[str] = Field(default=None, max_length=64)

    # ── Browser environment ───────────────────────────────────────────────────
    timezone:   Optional[str] = Field(default=None, max_length=50)
    user_agent: Optional[str] = Field(default=None, max_length=512)
    language:   Optional[str] = Field(default=None, max_length=20)
    platform:   Optional[str] = Field(default=None, max_length=50)

    # ── Bot / anti-detect signals ─────────────────────────────────────────────
    # These three are accessed by ScoringEngine._score_fingerprint()
    webdriver_detected: bool = Field(
        default=False,
        description=(
            "navigator.webdriver is truthy — Selenium / Playwright signal. "
            "Adds +30 to the fingerprint fraud sub-score."
        ),
    )
    headless_detected: bool = Field(
        default=False,
        description=(
            "Headless Chrome/Firefox detected via missing browser APIs. "
            "Adds +25 to the fingerprint fraud sub-score."
        ),
    )
    inconsistencies_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Count of contradictory browser property pairs detected by the "
            "JS collector (e.g. reported OS vs platform mismatch). "
            "≥ 3 adds +15 to the fingerprint fraud sub-score."
        ),
    )

    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# BehavioralSummary
# ─────────────────────────────────────────────────────────────────────────────

class BehavioralSummary(BaseModel):
    """
    Per-session behavioural signals aggregated by fraud-collector.js.

    POSTed to  POST /register/behavioral  on form submit.
    The session_token links this record to FingerprintPayload and to the
    BehavioralSession row created anonymously on page load.

    DB contract
    ───────────
    .model_dump(exclude={"session_token"}) is passed as **kwargs to
    FraudRepository.update_behavioral_session(session, user_id=user.id, **fields).
    That method calls setattr(session, key, value) for each pair, so every key
    MUST be a writable column on BehavioralSession.

    Read-only / ML-output columns intentionally absent from this schema:
        id, user_id, session_token, created_at, scored_at,
        ml_bot_probability, behavioral_score

    Used by
    ───────
    • api/v1/endpoints/registration.py   — request body type
    • services/fraud_scoring.py           — ScoringInput.behavioral field;
        accesses: rapid_completion, paste_detected, mouse_movement_count,
                  autofill_detected, touch_device
    • services/registration_service.py   — .session_token lookup,
        .model_dump(exclude={"session_token"}) → update_behavioral_session()
    • tasks/fraud_tasks.py               — reads the ORM row (same field names);
        accesses: rapid_completion, paste_detected, mouse_movement_count,
                  touch_device, typing_speed_avg_ms, form_time_seconds,
                  devtools_opened, tab_hidden_count
    """

    # ── Linking token (excluded from DB update) ───────────────────────────────
    session_token: str = Field(
        ...,
        min_length=10,
        max_length=64,
        description=(
            "Same token sent with FingerprintPayload. "
            "Used to look up and update the anonymous BehavioralSession row."
        ),
    )

    # ── Typing dynamics ───────────────────────────────────────────────────────
    typing_speed_avg_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Average inter-keystroke delay in ms. "
            "< 30 ms is humanly impossible; triggers +0.3 bot probability."
        ),
    )
    typing_speed_stddev: Optional[float] = Field(
        default=None,
        ge=0,
        description="Standard deviation of inter-keystroke delay. Very low variance = bot.",
    )
    paste_detected: bool = Field(
        default=False,
        description=(
            "Ctrl+V / right-click paste detected in any field. "
            "Combined with zero mouse movement: +0.4 bot probability."
        ),
    )
    autofill_detected: bool = Field(
        default=False,
        description=(
            "Browser autofill populated a field. "
            "Adds +10 to the behavioral fraud sub-score."
        ),
    )
    copy_detected: bool = Field(
        default=False,
        description="Ctrl+C or text-selection copy detected.",
    )
    field_focus_count: int = Field(default=0, ge=0, description="Total field-focus events.")
    field_blur_count:  int = Field(default=0, ge=0, description="Total field-blur events.")

    # ── Mouse / touch dynamics ────────────────────────────────────────────────
    mouse_movement_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Total mousemove events during the session. "
            "Zero on a non-touch desktop adds +20 to the behavioral score "
            "and +0.3 bot probability in the ML task."
        ),
    )
    click_count:      int             = Field(default=0, ge=0)
    scroll_depth_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Furthest page scroll depth reached (percent).",
    )
    touch_device: bool = Field(
        default=False,
        description=(
            "Touch events were detected. "
            "Exempts zero mouse_movement_count from being a bot signal."
        ),
    )
    hesitation_pauses: int = Field(
        default=0,
        ge=0,
        description="Pauses > 2 s between consecutive keystrokes — human-like hesitation marker.",
    )

    # ── Form timing ───────────────────────────────────────────────────────────
    form_time_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Seconds between first field focus and form submit. "
            "< 3 s triggers rapid_completion and +0.5 bot probability."
        ),
    )
    form_completion_ratio: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of required fields filled before submit (0.0 – 1.0).",
    )

    # ── Suspicion signals ─────────────────────────────────────────────────────
    devtools_opened: bool = Field(
        default=False,
        description=(
            "Chrome DevTools was opened during the session. "
            "Adds +0.2 bot probability in the ML task."
        ),
    )
    tab_hidden_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of visibilitychange events where the tab became hidden. "
            "> 5 adds +0.1 bot probability in the ML task."
        ),
    )
    rapid_completion: bool = Field(
        default=False,
        description=(
            "True when form_time_seconds < 3 — almost certainly a bot. "
            "Adds +50 to the behavioral fraud sub-score and +0.6 bot probability."
        ),
    )

    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# IDVerificationWebhook  (internal DTO — never exposed to clients)
# ─────────────────────────────────────────────────────────────────────────────

class IDVerificationWebhook(BaseModel):
    """
    Normalised identity-verification result DTO.

    Each provider maps its raw webhook body into this shape inside
    BaseIDVerificationProvider.parse_webhook().  IDVerificationService
    only ever receives this type — never the raw provider payload.

    Field access in IDVerificationService
    ──────────────────────────────────────
      process_webhook()     .provider_session_id, .status
      _handle_approved()    .id_number_hash, .id_type, .id_country,
                            .name_match, .dob_match
      _handle_rejected()    .rejection_reason
      _handle_expired()     (no fields beyond routing)

    Stripe parse_webhook() constructs with:
      provider, provider_session_id, status, id_number_hash, id_type,
      id_country, rejection_reason, raw_payload

    Onfido parse_webhook() constructs with:
      provider, provider_session_id, status, rejection_reason, raw_payload

    Stub parse_webhook() passes **raw_payload — must be tolerant of
    extra / missing fields; model_config extra="ignore" handles this.
    """

    # ── Provider identity ─────────────────────────────────────────────────────
    provider: str = Field(
        ...,
        max_length=30,
        description="'stripe' | 'onfido' | 'stub'",
    )
    provider_session_id: str = Field(
        ...,
        max_length=255,
        description=(
            "Provider's session / inquiry / applicant ID. "
            "Used to look up the IDVerification row via "
            "FraudRepository.get_verification_by_provider_session()."
        ),
    )

    # ── Outcome ───────────────────────────────────────────────────────────────
    status: Literal["approved", "rejected", "expired"] = Field(
        ...,
        description=(
            "'approved' → activate user, store ID hash, set id_verified=True\n"
            "'rejected' → keep PENDING_ID, allow retry\n"
            "'expired'  → session timed out, user must restart"
        ),
    )

    # ── Document data (approved sessions only) ────────────────────────────────
    # Raw ID numbers are NEVER stored. Providers extract them server-side;
    # only the one-way BLAKE2b hash arrives here via hash_id_number().
    id_number_hash: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "BLAKE2b-256 hex hash of the normalised government ID number. "
            "Used for duplicate-ID detection. Never store the raw number."
        ),
    )
    id_type: Optional[str] = Field(
        default=None,
        max_length=30,
        description="'passport' | 'national_id' | 'drivers_license'",
    )
    id_country: Optional[str] = Field(
        default=None,
        max_length=2,
        description="ISO 3166-1 alpha-2 code of the ID-issuing country.",
    )
    name_match: Optional[bool] = Field(
        default=None,
        description="Document name matches user's declared full_name.",
    )
    dob_match: Optional[bool] = Field(
        default=None,
        description="Document date-of-birth matches user's declared DOB.",
    )

    # ── Rejection detail ──────────────────────────────────────────────────────
    rejection_reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description=(
            "Provider rejection code or reason string. "
            "Examples: 'document_expired', 'face_mismatch', "
            "'id_already_registered', 'poor_image_quality'."
        ),
    )

    # ── Audit trail ───────────────────────────────────────────────────────────
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Unmodified JSON body from the provider's webhook POST. "
            "Stored for debugging and provider replay. "
            "Never surfaced to end-users."
        ),
    )

    # Tolerate extra keys from providers (e.g. Stripe sends many undocumented fields)
    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Initiate  (POST /register/initiate)
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationInitiateRequest(BaseModel):
    """
    Step 1 request: supply an identifier (email XOR phone) plus optional
    profile and fraud-collector.js signals.

    Identifier rules
    ────────────────
    Exactly one of email or phone_number must be present.
    Both absent or both present are rejected by the model validator.

    Username
    ────────
    Optional at this stage.  If omitted, registration_service.initiate()
    auto-generates one from the email local part or the last 6 phone digits.

    Fraud signals
    ─────────────
    fingerprint and behavioral are optional. Their absence slightly raises
    the fraud score but never alone causes a BLOCK.
    """

    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email address. Mutually exclusive with phone_number.",
    )
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="E.164 phone number, e.g. +12125551234. Mutually exclusive with email.",
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Desired username. Auto-generated if omitted.",
    )
    display_name: Optional[str] = Field(default=None, max_length=100)
    full_name:    Optional[str] = Field(default=None, max_length=200)
    country_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description=(
            "ISO 3166-1 alpha-2 country code declared by the user. "
            "Compared against geo-IP to compute the geo-mismatch fraud score."
        ),
    )
    language: str = Field(
        default="en",
        max_length=10,
        description="BCP-47 language tag, e.g. 'en', 'sw', 'fr'.",
    )
    fingerprint: Optional[FingerprintPayload] = Field(
        default=None,
        description="Browser fingerprint from fraud-collector.js.",
    )
    behavioral: Optional[BehavioralSummary] = Field(
        default=None,
        description="Behavioural summary from fraud-collector.js.",
    )

    @field_validator("phone_number", mode="before")
    @classmethod
    def _validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_e164(v)

    @field_validator("email", mode="before")
    @classmethod
    def _normalise_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else v

    @field_validator("country_code", mode="before")
    @classmethod
    def _uppercase_country(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v

    @model_validator(mode="after")
    def _exactly_one_identifier(self) -> "RegistrationInitiateRequest":
        has_email = bool(self.email)
        has_phone = bool(self.phone_number)
        if has_email and has_phone:
            raise ValueError(
                "Provide either an email address or a phone number — not both."
            )
        if not has_email and not has_phone:
            raise ValueError(
                "Please provide either an email address or a phone number."
            )
        return self

    model_config = {"extra": "ignore"}


class RegistrationInitiateResponse(BaseModel):
    """Step 1 response — tells the frontend where to send the user next."""

    action: str = Field(
        ...,
        description="'verify_email' | 'verify_phone'",
    )
    session_token: str = Field(
        ...,
        description=(
            "Opaque token stored in Redis as reg_otp:<token>. "
            "Must be echoed back in the Step 2 OTPVerifyRequest."
        ),
    )
    user_id: str = Field(
        ...,
        description="UUID of the newly created (bare) User row.",
    )
    message: str
    # Masked hints for the OTP delivery confirmation UI
    masked_email: Optional[str] = Field(
        default=None,
        description="e.g. 'jo**@gmail.com' — shown in the UI while the user waits for the code.",
    )
    masked_phone: Optional[str] = Field(
        default=None,
        description="e.g. '+1 **** 1234' — shown in the UI while the user waits for the code.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — OTP verification  (POST /register/verify-otp)
# ─────────────────────────────────────────────────────────────────────────────

class OTPVerifyRequest(BaseModel):
    """Step 2 request: the session_token from Step 1 + the 6-digit code."""

    session_token: str = Field(
        ...,
        description="Opaque token returned by RegistrationInitiateResponse.",
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit one-time code delivered by email or SMS.",
    )


class OTPVerifyResponse(BaseModel):
    """
    Step 2 response — returned after the OTP is accepted.

    Token naming note
    ─────────────────
    The field is named continuation_token (not verified_session_token) to
    match the key stored in Redis as reg_cont:<continuation_token> and the
    field expected by RegistrationCompleteRequest.continuation_token.
    """

    action: str = Field(
        default="set_password",
        description="Always 'set_password' — directs the frontend to the password step.",
    )
    continuation_token: str = Field(
        ...,
        description=(
            "Short-lived token (TTL 30 min) stored in Redis as "
            "reg_cont:<continuation_token>. "
            "Must be sent as RegistrationCompleteRequest.continuation_token. "
            "Proves that OTP verification was completed without exposing user_id."
        ),
    )
    message: str


class OTPResendRequest(BaseModel):
    """Request to resend the OTP for an in-progress Step 1 session."""

    session_token: str = Field(
        ...,
        description=(
            "The current session_token from RegistrationInitiateResponse. "
            "A new session_token is issued in the response; the old one is "
            "invalidated. 60-second cooldown is enforced."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Complete registration  (POST /register/complete)
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationCompleteRequest(BaseModel):
    """
    Step 3 request: exchange the continuation token for an active account
    by setting the password.

    The continuation_token proves the caller completed OTP verification (Step 2)
    without the user_id ever appearing in the client-side flow.

    Profile fields here overwrite any placeholders set in Step 1.
    Fraud signals can also be supplied here if they were not sent during Step 1
    (e.g. single-page apps that submit all signals together at the end).
    """

    continuation_token: str = Field(
        ...,
        description="Token from OTPVerifyResponse.continuation_token.",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Must satisfy the password strength policy (checked by validate_password_strength).",
    )
    display_name: Optional[str] = Field(default=None, max_length=100)
    full_name:    Optional[str] = Field(default=None, max_length=200)
    country_code: Optional[str] = Field(default=None, max_length=2)

    @field_validator("country_code", mode="before")
    @classmethod
    def _uppercase_country(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v

    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# Registration response  (returned by Step 3 and the legacy endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationResponse(BaseModel):
    """
    Terminal response from the registration pipeline.

    The frontend switches on action:

      "complete"
          Account is ACTIVE. Redirect to login or dashboard.

      "id_verification_pending"
          Password was set but the account is still PENDING_ID (fraud score
          triggered REVIEW and ID verification has not yet been approved).
          Show a "waiting for ID verification" screen.

      "id_verification_required"
          Fraud score triggered REVIEW during Step 1.  The user must complete
          government ID verification at verification_url before the account
          can be activated.  verification_session_id and verification_url
          are populated.

      "blocked"
          Fraud score triggered BLOCK. Show a generic "unable to create
          account" error — do not reveal the reason.

    ID-verification fields
    ──────────────────────
    Populated ONLY when action == "id_verification_required".
    The existing registration.py endpoint constructs this response from
    IDVerificationRequiredError.detail when a REVIEW score is triggered:

        return RegistrationResponse(
            action="id_verification_required",
            user_id=exc.detail.get("user_id"),
            verification_session_id=exc.detail.get("verification_session_id"),
            verification_url=exc.detail.get("verification_url"),
            message=exc.message,
        )
    """

    action: str = Field(
        ...,
        description=(
            "'complete' | 'id_verification_pending' | "
            "'id_verification_required' | 'blocked'"
        ),
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the user. Null only on hard fraud blocks (action='blocked').",
    )
    message: str = Field(..., description="Human-readable outcome summary.")

    # Populated only when action == "id_verification_required"
    verification_session_id: Optional[str] = Field(
        default=None,
        description=(
            "Provider session ID to store client-side for status polling. "
            "Only present when action == 'id_verification_required'."
        ),
    )
    verification_url: Optional[str] = Field(
        default=None,
        description=(
            "URL to redirect the user to for government ID verification. "
            "Only present when action == 'id_verification_required'."
        ),
    )

    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# RegistrationRequest  —  legacy single-step endpoint  (POST /register)
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationRequest(BaseModel):
    """
    Legacy single-step registration schema — still used by the existing
    POST /register endpoint in api/v1/endpoints/registration.py.

    Changes from earlier versions
    ──────────────────────────────
    • email is now Optional[str] (was EmailStr — required) so that the same
      schema can represent phone-only registrations.  At least one of email
      or phone_number is enforced by _at_least_one_identifier.
    • username is Optional (auto-generated by the service if omitted).
    • password is Optional (omitted in the three-step flow; required in the
      legacy single-step flow — enforced by _password_required_for_single_step).
    • country_code is auto-uppercased.
    • phone_number uses the shared _validate_e164 validator.

    New code should use the three-step flow
    (RegistrationInitiateRequest → OTPVerifyRequest → RegistrationCompleteRequest).
    """

    # ── Identifier (at least one required) ───────────────────────────────────
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email address. Required unless phone_number is supplied.",
    )
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="E.164 phone number. Required unless email is supplied.",
    )

    # ── Password (required in single-step; optional in three-step) ────────────
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        description=(
            "Required for the legacy single-step flow. "
            "Omit when using the three-step flow (set via /register/complete)."
        ),
    )

    # ── Profile ───────────────────────────────────────────────────────────────
    username:     Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Auto-generated if omitted.",
    )
    display_name: Optional[str] = Field(default=None, max_length=100)
    full_name:    Optional[str] = Field(default=None, max_length=200)
    country_code: Optional[str] = Field(default=None, max_length=2)
    language:     str           = Field(default="en", max_length=10)

    # ── Fraud signals ─────────────────────────────────────────────────────────
    fingerprint: Optional[FingerprintPayload] = None
    behavioral:  Optional[BehavioralSummary]  = None

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("phone_number", mode="before")
    @classmethod
    def _validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_e164(v)

    @field_validator("email", mode="before")
    @classmethod
    def _normalise_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else v

    @field_validator("country_code", mode="before")
    @classmethod
    def _uppercase_country(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v

    @model_validator(mode="after")
    def _at_least_one_identifier(self) -> "RegistrationRequest":
        has_email = bool(self.email)
        has_phone = bool(self.phone_number)
        if has_email and has_phone:
            raise ValueError(
                "Provide either an email address or a phone number — not both."
            )
        if not has_email and not has_phone:
            raise ValueError(
                "Please provide either an email address or a phone number."
            )
        return self

    model_config = {"extra": "ignore"}


# ─────────────────────────────────────────────────────────────────────────────
# RegistrationSession  —  Redis session model for the three-step flow
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationSession(BaseModel):
    """
    Value serialised as JSON and stored in Redis during the multi-step flow.

    Key schema
    ──────────
    Step 1 → 2:  reg_otp:<session_token>    TTL = 10 min
    Step 2 → 3:  reg_cont:<cont_token>      TTL = 30 min

    This class is the canonical definition of the reg_otp key payload.
    The reg_cont key stores only str(user_id) — no wrapper object needed.

    State machine
    ─────────────
    PENDING_OTP   — OTP sent, awaiting correct submission
    OTP_VERIFIED  — OTP accepted; awaiting Step 3 (set password)
    COMPLETE      — account created; this key has been deleted
    """

    state:            str            # "PENDING_OTP" | "OTP_VERIFIED" | "COMPLETE"
    delivery_channel: str            # "email" | "phone"
    email:            Optional[str]  = None
    phone_number:     Optional[str]  = None
    username:         Optional[str]  = None
    country_code:     Optional[str]  = None
    language:         str            = "en"
    # OTP state — stored here, never in DB
    otp_hash:         Optional[str]  = None   # SHA-256 hex of the raw 6-digit code
    otp_expires_at:   Optional[str]  = None   # ISO-8601 UTC string
    otp_attempts:     int            = 0
    otp_max_attempts: int            = 5
    otp_resend_count: int            = 0
    # Set after OTP verification (Step 2 → 3 bridge)
    continuation_token: Optional[str] = None
    # Link to fraud-collector.js session
    fraud_session_token: Optional[str] = None

    model_config = {"extra": "ignore"}
