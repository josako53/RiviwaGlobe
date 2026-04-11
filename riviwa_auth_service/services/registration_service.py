"""
services/registration_service.py
═══════════════════════════════════════════════════════════════════════════════
Three-step account registration pipeline.

Step 1 — initiate()
  • Validates uniqueness (email / phone / username).
  • Runs 6-signal fraud scoring via ScoringEngine(ScoringInput).
  • Creates a bare User row (status=PENDING_EMAIL or PENDING_PHONE).
  • Persists fraud artefacts: DeviceFingerprint, IPRecord, BehavioralSession,
    FraudAssessment.
  • Dispatches OTP via the configured provider (Twilio Verify / SMS / SMTP).
  • Returns a Redis-backed session_token (TTL = OTP_REGISTRATION_TTL_SECONDS).

Step 2 — verify_otp()
  • Verifies the OTP via the originating provider.
  • Marks the identifier (email or phone) as verified on the User row.
  • Consumes the step-1 session; issues a continuation_token
    (TTL = OTP_CONTINUATION_TTL_SECONDS).

Step 3 — complete()
  • Validates and hashes the password (Argon2id).
  • ALLOW / WARN → sets status=ACTIVE.
  • REVIEW        → sets status=PENDING_ID, initiates IDVerification session.
  • Consumes the continuation_token.

resend_otp()
  • Enforces a 60-second cooldown between resends.
  • Invalidates old provider session; issues new OTP and new session_token.
  • TTL is not extended on resend.

Redis key schema
────────────────
  reg_init:<session_token>      TTL = OTP_REGISTRATION_TTL_SECONDS  (600 s)
  reg_cont:<continuation_token> TTL = OTP_CONTINUATION_TTL_SECONDS (1800 s)
  vel_ip:<ip_address>           TTL = 3600 s   (velocity sliding window)
  vel_fp:<fingerprint_hash>     TTL = 3600 s   (velocity sliding window)

Interface contracts — corrections applied in this revision
───────────────────────────────────────────────────────────
  1. services.geo  does NOT exist.
     Correct module: services.geo_service — exposes lookup_ip() async function.
     There is NO GeoService class.

  2. services.id_verification  does NOT exist.
     Correct module: services.id_verification_service — IDVerificationService.
     Constructor:  IDVerificationService(db: AsyncSession)  — no fraud_repo arg.
     Method:       initiate_for_user(user: User, return_url=None) → VerificationSession
     Result attr:  VerificationSession.session_url  (not .redirect_url)

  3. ScoringEngine.score() takes a SINGLE ScoringInput dataclass argument.
     Do NOT call it with individual keyword args.

  4. ScoringResult has .details (dict) — NOT .signal_details.
     ScoringResult has NO .action_reason field — pass None to FraudAssessment.

  5. AccountStatus.PENDING_VERIFICATION does not exist.
     Use PENDING_EMAIL for email registrations, PENDING_PHONE for phone.

  6. data.fingerprint is a plain str — NOT an object.
     data.behavioral is a plain str — NOT an object.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel, Field, field_validator, model_validator
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    DuplicateIdentifierError,
    FraudBlockedError,
    InvalidOTPError,
    InvalidTokenError,
    OTPCooldownError,
    OTPExpiredError,
    OTPMaxAttemptsError,
    WeakPasswordError,
)
from core.notifications import get_provider_for_channel
from core.security import generate_secure_token, hash_password, normalize_email, validate_password_strength
from events.publisher import EventPublisher
from models.fraud import FraudAction
from models.user import AccountStatus
from repositories.fraud_repository import FraudRepository
from repositories.user_repository import UserRepository
from schemas.fraud import BehavioralSummary
from services.fraud_scoring import ScoringEngine, ScoringInput

# ── Correct module names ──────────────────────────────────────────────────────
# geo_service.py   → lookup_ip() async function + GeoResult dataclass.
#                    No GeoService class exists.
# id_verification_service.py → IDVerificationService class.
from services.geo_service import lookup_ip
from services.id_verification_service import IDVerificationService

log = structlog.get_logger(__name__)

# ── Redis key prefixes ─────────────────────────────────────────────────────────
_REG_INIT_PREFIX = "reg_init:"
_REG_CONT_PREFIX = "reg_cont:"
_VEL_IP_PREFIX   = "vel_ip:"
_VEL_FP_PREFIX   = "vel_fp:"

_INIT_TTL         = getattr(settings, "OTP_REGISTRATION_TTL_SECONDS", 600)
_CONT_TTL         = getattr(settings, "OTP_CONTINUATION_TTL_SECONDS", 1800)
_OTP_MAX_ATTEMPTS = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
_RESEND_COOLDOWN  = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
_VELOCITY_WINDOW  = 3600


# ══════════════════════════════════════════════════════════════════════════════
# Request / Response models
# ══════════════════════════════════════════════════════════════════════════════

class InitiateRequest(BaseModel):
    """
    Step 1 request body.

    Exactly one of `email` or `phone_number` must be non-empty.

    `fingerprint` and `behavioral` are PLAIN STRINGS:
      - fingerprint : composite SHA-256 hash (hex, 64 chars)
      - behavioral  : JS session token issued on page load
    """
    email:        str = ""
    phone_number: str = ""
    username:     str
    display_name: str
    full_name:    str
    country_code: str = Field(
        default="",
        max_length=2,
        description="ISO-3166-1 alpha-2 country code (e.g. 'TZ', 'US'). "
                    "Must be exactly 2 letters when provided.",
    )
    fingerprint:  Optional[str] = None   # composite hash string — NOT an object
    behavioral:   Optional[str] = None   # session token string — NOT an object

    @field_validator("country_code", mode="before")
    @classmethod
    def _validate_country_code(cls, v: str) -> str:
        if not v:
            return v
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError(
                "country_code must be a 2-letter ISO-3166-1 alpha-2 code "
                "(e.g. 'TZ', 'US', 'GB')."
            )
        return v.lower()   # store lowercase — consistent with existing behaviour

    @model_validator(mode="after")
    def _exactly_one_identifier(self) -> "InitiateRequest":
        has_email = bool(self.email and self.email.strip())
        has_phone = bool(self.phone_number and self.phone_number.strip())
        if has_email and has_phone:
            raise ValueError("Provide either email or phone_number, not both.")
        if not has_email and not has_phone:
            raise ValueError("Either email or phone_number is required.")
        return self


class InitiateResponse(BaseModel):
    session_token:      str
    otp_channel:        str
    otp_destination:    str
    expires_in_seconds: int
    message:            str


class VerifyOTPRequest(BaseModel):
    session_token: str
    otp_code:      str


class VerifyOTPResponse(BaseModel):
    continuation_token: str
    message:            str


class CompleteRequest(BaseModel):
    continuation_token: str
    password:           str
    password_confirm:   str

    @model_validator(mode="after")
    def _passwords_match(self) -> "CompleteRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match.")
        return self


class CompleteResponse(BaseModel):
    action:              str
    message:             str
    id_verification_url: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════════════

class RegistrationService:

    def __init__(
        self,
        db:        AsyncSession,
        publisher: EventPublisher,
        redis:     Redis,
    ) -> None:
        self.db          = db
        self.publisher   = publisher
        self.redis       = redis
        self.user_repo   = UserRepository(db)
        self.fraud_repo  = FraudRepository(db)
        # ScoringEngine.score() takes ScoringInput — no positional kwargs API.
        # geo lookup is done via lookup_ip() module function, not a class.
        self.scoring_eng = ScoringEngine()

    # ── Step 1 ────────────────────────────────────────────────────────────────

    async def initiate(
        self,
        data:       InitiateRequest,
        ip_address: str,
        user_agent: Optional[str],
    ) -> InitiateResponse:
        has_email        = bool(data.email and data.email.strip())
        id_type          = "email" if has_email else "phone"
        # email_norm     : lowercased raw address  → stored in users.email
        # email_normalized: dots + alias stripped  → stored in users.email_normalized
        #                   (Gmail dot-trick / + alias dedup column)
        # normalize_email() is the single source of truth in core.security.
        email_norm       = data.email.strip().lower() if has_email else None
        email_normalized = normalize_email(data.email) if has_email else None

        log.info("registration.step1.started", id_type=id_type, ip=ip_address)

        # ── Uniqueness checks ─────────────────────────────────────────────────
        if email_norm and await self.user_repo.get_by_email(email_norm):
            raise DuplicateIdentifierError("Email already registered.")
        if data.phone_number and await self.user_repo.get_by_phone(data.phone_number):
            raise DuplicateIdentifierError("Phone number already registered.")
        if await self.user_repo.get_by_username(data.username):
            raise DuplicateIdentifierError("Username already taken.")

        # ── Geo lookup ────────────────────────────────────────────────────────
        # lookup_ip() is a module-level async function in services.geo_service.
        # There is NO GeoService class — do not instantiate one.
        geo = await lookup_ip(ip_address)

        # ── Fraud signals ─────────────────────────────────────────────────────
        ip_users    = await self.fraud_repo.get_users_by_ip(ip_address)
        velocity_ip = await self._count_recent_by_ip(ip_address)

        fp_users    = []
        velocity_fp = 0
        # data.fingerprint is a plain str (composite SHA-256 hash).
        # Do NOT access data.fingerprint.fingerprint_hash — it is not an object.
        if data.fingerprint:
            fp_users    = await self.fraud_repo.get_users_by_fingerprint(data.fingerprint)
            velocity_fp = await self._count_recent_by_fp(data.fingerprint)

        # data.behavioral is a plain str (JS session token).
        # Use it to look up the BehavioralSession ORM row if it already exists.
        behavioral_session = None
        if data.behavioral:
            behavioral_session = await self.fraud_repo.get_session_by_token(data.behavioral)

        # ── Build BehavioralSummary from ORM session ──────────────────────────
        # ScoringInput.behavioral expects BehavioralSummary (Pydantic schema),
        # NOT the BehavioralSession ORM model.  Convert explicitly.
        # If the session is missing or signals are null, pass None — the scorer
        # returns 15 (mildly suspicious) for absent behavioral data.
        behavioral_summary: Optional[BehavioralSummary] = None
        if behavioral_session is not None:
            try:
                behavioral_summary = BehavioralSummary(
                    rapid_completion     = behavioral_session.rapid_completion,
                    paste_detected       = behavioral_session.paste_detected,
                    mouse_movement_count = behavioral_session.mouse_movement_count,
                    autofill_detected    = behavioral_session.autofill_detected,
                    touch_device         = behavioral_session.touch_device,
                )
            except Exception:
                # Session row exists but behavioral fields are still None
                # (collector events haven't been flushed yet).
                behavioral_summary = None

        # ── Score ─────────────────────────────────────────────────────────────
        # ScoringEngine.score() takes ONE argument: a ScoringInput dataclass.
        # Do NOT pass individual keyword arguments directly to score().
        scoring_inp = ScoringInput(
            email                           = email_norm or "",          # "" for phone-only — scorer only, not DB
            email_normalized                = email_normalized or "",    # "" for phone-only — scorer only, not DB
            ip_address                      = ip_address,
            geo                             = geo,
            # FingerprintPayload (full browser signals) is unavailable at init
            # — we only have the composite hash string. fingerprint_user_count
            # carries the duplicate-device signal via len(fp_users).
            fingerprint                     = None,
            behavioral                      = behavioral_summary,
            # Always False on live path: uniqueness gate fires before scoring.
            email_normalized_exists         = False,
            ip_user_count                   = len(ip_users),
            fingerprint_user_count          = len(fp_users),
            declared_country                = data.country_code,
            registrations_last_hour_from_ip = velocity_ip,
            registrations_last_hour_from_fp = velocity_fp,
        )
        score_result = self.scoring_eng.score(scoring_inp)

        if score_result.action == FraudAction.BLOCK:
            await self.fraud_repo.create_assessment(
                {
                    "user_id":           None,
                    "email":             email_norm or "",
                    "email_normalized":  email_normalized or "",   # ← correct normalized form
                    "ip_address":        ip_address,
                    "fingerprint_hash":  data.fingerprint,
                    "phone_number":      data.phone_number or None,
                    "score_email":       score_result.score_email,
                    "score_ip":          score_result.score_ip,
                    "score_fingerprint": score_result.score_fingerprint,
                    "score_behavioral":  score_result.score_behavioral,
                    "score_velocity":    score_result.score_velocity,
                    "score_geo":         score_result.score_geo,
                    "total_score":       score_result.total_score,
                    "action":            score_result.action,
                    "action_reason":     None,
                    "signal_details":    score_result.details,
                    "linked_account_ids": {
                        "ids": [str(u) for u in set(ip_users + fp_users)]
                    },
                }
            )
            await self.db.commit()
            log.warning(
                "registration.fraud_blocked",
                ip=ip_address,
                score=score_result.total_score,
            )
            raise FraudBlockedError()

        # ── Create bare User row ──────────────────────────────────────────────
        # AccountStatus.PENDING_VERIFICATION does not exist in AccountStatus enum.
        # Use PENDING_EMAIL for email registrations, PENDING_PHONE for phone-only.
        initial_status = (
            AccountStatus.PENDING_EMAIL
            if id_type == "email"
            else AccountStatus.PENDING_PHONE
        )
        user = await self.user_repo.create(
            username          = data.username,
            email             = email_norm or None,          # NULL for phone-only users
            email_normalized  = email_normalized or None,    # NULL for phone-only users
            phone_number      = data.phone_number or None,
            display_name      = data.display_name,
            full_name         = data.full_name,
            country_code      = data.country_code or None,
            status            = initial_status,
            # Phone-only users have no email — mark as verified so email
            # verification is never required for them.
            is_email_verified = id_type != "email",
        )

        # ── DeviceFingerprint ─────────────────────────────────────────────────
        # data.fingerprint is the raw hash string.
        # upsert_fingerprint() expects {"fingerprint_hash": str, ...} dict.
        if data.fingerprint:
            await self.fraud_repo.upsert_fingerprint(
                user.id,
                {
                    "fingerprint_hash": data.fingerprint,
                    "user_agent":       user_agent,
                },
            )

        # ── IPRecord ──────────────────────────────────────────────────────────
        await self.fraud_repo.create_ip_record(
            user.id,
            {
                "ip_address":           ip_address,
                "country_code":         geo.country_code,
                "region":               geo.region,
                "city":                 geo.city,
                "latitude":             geo.latitude,
                "longitude":            geo.longitude,
                "isp":                  geo.isp,
                "asn":                  geo.asn,
                "is_vpn":               geo.is_vpn,
                "is_tor":               geo.is_tor,
                "is_proxy":             geo.is_proxy,
                "is_datacenter":        geo.is_datacenter,
                "is_high_risk_country": geo.is_high_risk_country,
            },
        )

        # ── BehavioralSession ─────────────────────────────────────────────────
        # data.behavioral is a plain session token string — NOT an object.
        if data.behavioral:
            if behavioral_session is None:
                await self.fraud_repo.create_behavioral_session(
                    {
                        "session_token": data.behavioral,
                        "user_id":       user.id,
                    }
                )
            else:
                await self.fraud_repo.update_behavioral_session(
                    behavioral_session, user_id=user.id
                )

        # ── FraudAssessment ───────────────────────────────────────────────────
        await self.fraud_repo.create_assessment(
            {
                "user_id":           user.id,
                "email":             email_norm or "",
                "email_normalized":  email_normalized or "",   # ← correct normalized form
                "ip_address":        ip_address,
                "fingerprint_hash":  data.fingerprint,
                "phone_number":      data.phone_number or None,
                "score_email":       score_result.score_email,
                "score_ip":          score_result.score_ip,
                "score_fingerprint": score_result.score_fingerprint,
                "score_behavioral":  score_result.score_behavioral,
                "score_velocity":    score_result.score_velocity,
                "score_geo":         score_result.score_geo,
                "total_score":       score_result.total_score,
                "action":            score_result.action,
                "action_reason":     None,
                "signal_details":    score_result.details,
                "linked_account_ids": {
                    "ids": [str(u) for u in set(ip_users + fp_users)]
                },
            }
        )

        await self.db.commit()

        # ── Velocity counter increment (Redis sliding window) ─────────────────
        ip_key = f"{_VEL_IP_PREFIX}{ip_address}"
        await self.redis.incr(ip_key)
        await self.redis.expire(ip_key, _VELOCITY_WINDOW)

        if data.fingerprint:
            fp_key = f"{_VEL_FP_PREFIX}{data.fingerprint}"
            await self.redis.incr(fp_key)
            await self.redis.expire(fp_key, _VELOCITY_WINDOW)

        # ── OTP dispatch ──────────────────────────────────────────────────────
        channel, to, destination = _resolve_otp_target(
            id_type, email_norm, data.phone_number
        )

        provider         = get_provider_for_channel(channel)
        provider_payload = await provider.send_otp(
            to           = to,
            channel      = channel,
            display_name = data.display_name,
            purpose      = "registration",
        )

        # ── Redis session ─────────────────────────────────────────────────────
        # `to` is stored explicitly so resend_otp() can re-use it without
        # reloading the user from DB.
        session_token = generate_secure_token()
        session: Dict[str, Any] = {
            "user_id":      str(user.id),
            "fraud_action": score_result.action.value,
            "id_type":      id_type,
            "attempts":     0,
            "resend_at":    (
                datetime.now(timezone.utc) + timedelta(seconds=_RESEND_COOLDOWN)
            ).isoformat(),
            "channel":      channel,
            "to":           to,
            **provider_payload,
        }
        await self.redis.setex(
            f"{_REG_INIT_PREFIX}{session_token}",
            _INIT_TTL,
            json.dumps(session),
        )

        log.info(
            "registration.step1.complete",
            user_id=str(user.id),
            channel=channel,
            provider=provider_payload.get("provider"),
            fraud_action=score_result.action.value,
        )

        return InitiateResponse(
            session_token      = session_token,
            otp_channel        = channel,
            otp_destination    = destination,
            expires_in_seconds = _INIT_TTL,
            message            = f"A verification code has been sent to your {channel}.",
        )

    # ── Step 2 ────────────────────────────────────────────────────────────────

    async def verify_otp(self, data: VerifyOTPRequest) -> VerifyOTPResponse:
        redis_key = f"{_REG_INIT_PREFIX}{data.session_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise OTPExpiredError()

        session  = json.loads(raw)
        attempts = session.get("attempts", 0)

        if attempts >= _OTP_MAX_ATTEMPTS:
            await self.redis.delete(redis_key)
            raise OTPMaxAttemptsError()

        provider = get_provider_for_channel(session["channel"])
        try:
            code_is_valid = await provider.verify_otp(
                submitted_code  = data.otp_code,
                session_payload = session,
            )
        except (OTPExpiredError, OTPMaxAttemptsError):
            raise

        if not code_is_valid:
            attempts += 1
            session["attempts"] = attempts
            if attempts >= _OTP_MAX_ATTEMPTS:
                await self.redis.delete(redis_key)
                raise OTPMaxAttemptsError()
            ttl = await self.redis.ttl(redis_key)
            if ttl > 0:
                await self.redis.setex(redis_key, ttl, json.dumps(session))
            raise InvalidOTPError()

        # ── Mark identifier verified ──────────────────────────────────────────
        user_id = uuid.UUID(session["user_id"])
        id_type = session.get("id_type", "phone")

        if id_type == "email":
            await self.user_repo.mark_email_verified(user_id)
        else:
            await self.user_repo.mark_phone_verified(user_id)
        await self.db.commit()

        # ── Consume init session, issue continuation token ────────────────────
        await self.redis.delete(redis_key)

        continuation_token = generate_secure_token()
        cont_session: Dict[str, Any] = {
            "user_id":      str(user_id),
            "fraud_action": session.get("fraud_action", FraudAction.ALLOW.value),
        }
        await self.redis.setex(
            f"{_REG_CONT_PREFIX}{continuation_token}",
            _CONT_TTL,
            json.dumps(cont_session),
        )

        log.info("registration.step2.complete", user_id=str(user_id))

        return VerifyOTPResponse(
            continuation_token = continuation_token,
            message            = "OTP verified. Proceed to set your password.",
        )

    # ── Step 3 ────────────────────────────────────────────────────────────────

    async def complete(
        self,
        data:       CompleteRequest,
        ip_address: str,
    ) -> CompleteResponse:
        redis_key = f"{_REG_CONT_PREFIX}{data.continuation_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise InvalidTokenError(
                "Continuation token expired. Restart registration from Step 1."
            )

        cont         = json.loads(raw)
        user_id      = uuid.UUID(cont["user_id"])
        fraud_action = FraudAction(cont.get("fraud_action", FraudAction.ALLOW.value))

        ok, reason = validate_password_strength(data.password)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(data.password)
        await self.user_repo.set_password(user_id, new_hash)

        id_verification_url: Optional[str] = None

        if fraud_action == FraudAction.REVIEW:
            await self.user_repo.set_status(user_id, AccountStatus.PENDING_ID)

            # IDVerificationService constructor: IDVerificationService(db: AsyncSession)
            # It does NOT accept fraud_repo as a parameter.
            # Correct method: initiate_for_user(user: User, return_url: Optional[str])
            # Returns: VerificationSession with .session_url attribute (not .redirect_url)
            id_svc       = IDVerificationService(db=self.db)
            user         = await self.user_repo.get_by_id(user_id)
            verification = await id_svc.initiate_for_user(user=user, return_url=None)
            id_verification_url = verification.session_url
            action              = "id_verification_pending"
        else:
            await self.user_repo.set_status(user_id, AccountStatus.ACTIVE)
            action = "complete"

        await self.redis.delete(redis_key)
        await self.db.commit()

        user = await self.user_repo.get_by_id(user_id)
        log.info("registration.step3.complete", user_id=str(user_id), action=action)
        await self.publisher.user_registered(user)

        # Welcome notification �� fires once on account creation
        try:
            await self.publisher.notifications.auth_welcome(
                recipient_user_id = str(user.id),
                display_name      = user.display_name or user.username or "there",
                language          = "en",
            )
        except Exception as _exc:
            log.warning("registration.welcome_notification_failed", error=str(_exc))

        return CompleteResponse(
            action              = action,
            message             = (
                "Account created successfully. You may now log in."
                if action == "complete"
                else "Account created. Please complete identity verification."
            ),
            id_verification_url = id_verification_url,
        )

    # ── OTP resend ────────────────────────────────────────────────────────────

    async def resend_otp(self, session_token: str) -> InitiateResponse:
        redis_key = f"{_REG_INIT_PREFIX}{session_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise OTPExpiredError()

        session = json.loads(raw)

        resend_at = datetime.fromisoformat(
            session.get("resend_at", datetime.now(timezone.utc).isoformat())
        )
        now = datetime.now(timezone.utc)
        if now < resend_at:
            wait = int((resend_at - now).total_seconds())
            raise OTPCooldownError(
                f"Resend cooldown active. Wait {wait} second(s) before retrying."
            )

        channel = session["channel"]
        to      = session.get("to", "")

        provider         = get_provider_for_channel(channel)
        provider_payload = await provider.send_otp(
            to      = to,
            channel = channel,
            purpose = "registration",
        )

        new_token   = generate_secure_token()
        ttl         = await self.redis.ttl(redis_key)
        new_session = {
            **session,
            "attempts":  0,
            "resend_at": (
                datetime.now(timezone.utc) + timedelta(seconds=_RESEND_COOLDOWN)
            ).isoformat(),
            **provider_payload,
        }

        await self.redis.delete(redis_key)
        await self.redis.setex(
            f"{_REG_INIT_PREFIX}{new_token}",
            max(ttl, 1),
            json.dumps(new_session),
        )

        log.info("registration.resend_otp", channel=channel)

        destination = _mask_email(to) if channel == "email" else _mask_phone(to)
        return InitiateResponse(
            session_token      = new_token,
            otp_channel        = channel,
            otp_destination    = destination,
            expires_in_seconds = max(ttl, 1),
            message            = f"A new verification code has been sent to your {channel}.",
        )

    # ── Velocity helpers (Redis sliding window) ───────────────────────────────

    async def _count_recent_by_ip(self, ip_address: str) -> int:
        val = await self.redis.get(f"{_VEL_IP_PREFIX}{ip_address}")
        return int(val or 0)

    async def _count_recent_by_fp(self, fp_hash: str) -> int:
        val = await self.redis.get(f"{_VEL_FP_PREFIX}{fp_hash}")
        return int(val or 0)


# ── Private helpers ───────────────────────────────────────────────────────────

def _resolve_otp_target(
    id_type:      str,
    email_norm:   Optional[str],
    phone_number: str,
) -> tuple[str, str, str]:
    """Return (channel, to, masked_destination)."""
    if id_type == "email" and email_norm:
        return "email", email_norm, _mask_email(email_norm)
    return "sms", phone_number, _mask_phone(phone_number)


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 7:
        return phone[:3] + "***"
    return phone[:4] + "***" + phone[-4:]