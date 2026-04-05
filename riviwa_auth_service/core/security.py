"""
core/security.py
═══════════════════════════════════════════════════════════════════════════════
All cryptographic and security primitives for the Riviwa auth service.

Responsibilities
────────────────
  Password hashing / verification      Argon2id via passlib
  JWT access token creation/decoding   python-jose HS256
  Refresh token generation             opaque random string → Redis
  OTP generation + hashing             secrets.randbelow → SHA-256
  Secure link token generation         secrets.token_urlsafe → SHA-256
  Password strength validation         regex policy (OWASP)
  Email normalisation                  duplicate-account detection guard
  Sensitive ID hashing                 BLAKE2b (government ID numbers)

─────────────────────────────────────────────────────────────────────────────
Why Argon2id?
  Winner of the Password Hashing Competition (2015). Memory-hard (GPU/ASIC
  resistant) and hybrid (side-channel resistant). Recommended by OWASP and
  NIST SP 800-63B for interactive logins.

  Parameters (OWASP interactive-login minimums):
      type         = id  (hybrid; resistant to both side-channel and GPU)
      time_cost    = 2   iterations
      memory_cost  = 65 536 KiB  (64 MiB)
      parallelism  = 2
      hash_len     = 32 bytes output
      salt_size    = 16 bytes (auto-generated per hash)

Why HS256 JWT?
  Symmetric — one SECRET_KEY signs and verifies.
  Correct for a monolithic auth service where issuance == verification.
  Upgrade to RS256 / ES256 when external services must verify independently.

Refresh token design
  Opaque URL-safe random string, never a JWT.
  Stored as:  Redis "refresh:<token>" → user_id   TTL = REFRESH_TOKEN_EXPIRE_DAYS
  Rotated on every use; revoked immediately on logout.

JTI deny-list (logout / token rotation)
  On logout the JTI is stored in Redis:
      "jti_deny:<jti>" → "1"   TTL = remaining access token seconds
  The get_current_token dependency checks this before trusting any token.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.exceptions import AccessTokenExpiredError, UnauthorisedError

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Argon2id password context
# ─────────────────────────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    # Argon2id with OWASP interactive-login minimums
    argon2__type="id",
    argon2__time_cost=2,
    argon2__memory_cost=65_536,   # 64 MiB
    argon2__parallelism=2,
    argon2__hash_len=32,
    argon2__salt_size=16,
)


def hash_password(plain: str) -> str:
    """
    Return an Argon2id hash of *plain*.

    Stored format (all parameters included in the string):
        $argon2id$v=19$m=65536,t=2,p=2$<base64-salt>$<base64-hash>

    The raw password is NEVER stored or logged anywhere.
    """
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Constant-time verify *plain* against an Argon2id *hashed* string.

    passlib automatically rehashes if parameters have drifted (transparent
    upgrade via the deprecated="auto" setting).
    Returns True on match, False otherwise.
    """
    return _pwd_context.verify(plain, hashed)


def needs_rehash(hashed: str) -> bool:
    """
    True when the stored hash was computed with outdated parameters.
    Call after a successful verify_password(); if True, rehash with
    hash_password() and persist the new hash transparently.
    """
    return _pwd_context.needs_update(hashed)


# ─────────────────────────────────────────────────────────────────────────────
# Password strength validation
# ─────────────────────────────────────────────────────────────────────────────

# 8+ chars, at least one each of: uppercase, lowercase, digit, special char.
_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
    r"(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]).{8,}$"
)

_PASSWORD_POLICY_MSG = (
    "Password must be at least 8 characters long and include at least one "
    "uppercase letter, one lowercase letter, one digit, and one special "
    "character (e.g. ! @ # $ % ^ & *)."
)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Server-side password policy check.

    Returns:
        (True,  "")             → password meets policy
        (False, reason_string)  → password rejected

    Called by RegistrationService and ChangePasswordService as a server-side
    guard even though the Pydantic schema layer also validates at the API boundary.
    """
    if not _PASSWORD_RE.match(password):
        return False, _PASSWORD_POLICY_MSG
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Email normalisation  (duplicate-account guard)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_email(email: str) -> str:
    """
    Produce the canonical form of an email address used ONLY for duplicate
    detection via the email_normalized UNIQUE constraint on users.

    The original email is always stored as-typed in the email column.
    Only this normalised form has the uniqueness constraint.

    Rules applied
    ─────────────
    1.  Lowercase + strip whitespace.
    2.  Remove the +alias suffix from the local part (universal).
    3.  For Gmail / Googlemail:
            a. Strip all dots from the local part.
            b. Normalise googlemail.com → gmail.com.

    Examples
    ────────
    j.doe+work@gmail.com   →   jdoe@gmail.com
    John+tag@GMAIL.COM     →   john@gmail.com
    john@googlemail.com    →   john@gmail.com
    alice@company.com      →   alice@company.com   (non-Gmail unchanged)
    """
    email  = email.strip().lower()
    local, _, domain = email.partition("@")

    # Remove + alias (applies to all providers)
    local = local.split("+")[0]

    # Gmail-specific normalisations
    if domain in ("gmail.com", "googlemail.com"):
        local  = local.replace(".", "")
        domain = "gmail.com"

    return f"{local}@{domain}"


# ─────────────────────────────────────────────────────────────────────────────
# JWT access tokens
# ─────────────────────────────────────────────────────────────────────────────

def create_access_token(
    *,
    user_id:       uuid.UUID,
    org_id:        Optional[uuid.UUID] = None,
    org_role:      Optional[str]       = None,
    platform_role: Optional[str]       = None,
) -> tuple[str, str, int]:
    """
    Create a signed HS256 JWT access token.

    JWT claims included
    ───────────────────
        sub            user UUID string           (always)
        jti            token UUID                 (always; used for deny-list)
        iat            issued-at Unix timestamp   (always)
        exp            expiry Unix timestamp      (always)
        org_id         active org UUID string     (omitted when personal view)
        org_role       member role in active org  (omitted when personal view)
        platform_role  super_admin|admin|moderator (omitted when not staff)

    Returns
    ───────
        (encoded_jwt, jti_str, expires_in_seconds)

    The jti is returned so the caller can store it in Redis on logout
    without having to decode the token again.
    """
    now        = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti        = str(uuid.uuid4())

    payload: dict = {
        "sub": str(user_id),
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if org_id is not None:
        payload["org_id"] = str(org_id)
    if org_role:
        payload["org_role"] = org_role
    if platform_role:
        payload["platform_role"] = platform_role

    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    expires_in = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    log.debug("jwt.issued", user_id=str(user_id), jti=jti, expires_in=expires_in)
    return encoded, jti, expires_in


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises
    ──────
        AccessTokenExpiredError   exp claim is in the past
        UnauthorisedError         bad signature, malformed, or any other JWTError

    Returns the raw claims dict on success.
    The caller (auth dependency) MUST ALSO check the JTI against the Redis
    deny-list before trusting the token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )
        return payload
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise AccessTokenExpiredError() from exc
        raise UnauthorisedError("JWT verification failed.") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Refresh tokens  (opaque, stored in Redis)
# ─────────────────────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure opaque refresh token.

    32 bytes via secrets.token_urlsafe → 43 URL-safe base64 chars → 256 bits.

    Storage:   Redis "refresh:<token>" → user_id
    TTL:       settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    Rotation:  old key deleted, new key stored on every token refresh call.
    Never written to the database.
    """
    return secrets.token_urlsafe(32)


# ─────────────────────────────────────────────────────────────────────────────
# OTP  (6-digit one-time codes via OS CSPRNG)
# ─────────────────────────────────────────────────────────────────────────────

_OTP_DIGITS = 6


def generate_otp() -> str:
    """
    Generate a 6-digit OTP using the OS CSPRNG.

    secrets.randbelow(10 ** 6) → uniform integer in [0, 999999].
    Zero-padded to 6 digits.

    The raw code is delivered to the user via email/SMS.
    Only sha256(raw_code) is stored server-side.
    """
    code = secrets.randbelow(10 ** _OTP_DIGITS)
    return str(code).zfill(_OTP_DIGITS)


def hash_otp(raw_otp: str) -> str:
    """SHA-256 hex digest of the raw OTP string.  Stored in Redis, not the DB."""
    return hashlib.sha256(raw_otp.encode()).hexdigest()


def verify_otp(submitted: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of sha256(submitted) against stored_hash.
    Uses hmac.compare_digest to prevent timing oracle attacks.
    """
    candidate = hashlib.sha256(submitted.encode()).hexdigest()
    return hmac.compare_digest(candidate, stored_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Secure link tokens  (email verification, password reset, org invites)
# ─────────────────────────────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    """
    URL-safe random token for use in email / SMS links.

    32 bytes → 43 URL-safe base64 chars → 256 bits of entropy.

    Pattern:
        raw_token  = generate_secure_token()     # emailed to user
        token_hash = hash_token(raw_token)       # stored in DB
        # On redemption: verify_token(submitted_raw, stored_hash)
    """
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """
    SHA-256 hash of a raw link token.

    Only the hash is stored in the database (password_reset_tokens,
    organisation_invites).  The raw token is sent to the user and is
    never persisted — even a full DB dump cannot be replayed.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


def verify_token(raw_token: str, stored_hash: str) -> bool:
    """Constant-time comparison of sha256(raw_token) against stored_hash."""
    candidate = hashlib.sha256(raw_token.encode()).hexdigest()
    return hmac.compare_digest(candidate, stored_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Session tokens  (opaque Redis keys for multi-step auth flows)
# ─────────────────────────────────────────────────────────────────────────────

def generate_session_token() -> str:
    """
    Generate an opaque session token for multi-step auth / verification flows.

    Used as Redis key prefixes:
        reg:<token>       → registration session
        login:<token>     → login MFA session
        pwd_reset:<token> → password-reset session

    32 bytes → 256 bits → collision-resistant at any realistic scale.
    """
    return secrets.token_urlsafe(32)


# ─────────────────────────────────────────────────────────────────────────────
# Sensitive ID hashing  (government ID numbers)
# ─────────────────────────────────────────────────────────────────────────────

def hash_sensitive_id(raw_id: str) -> str:
    """
    One-way BLAKE2b hash of a government ID number.

    Rules enforced here:
        · Normalise to uppercase and strip spaces before hashing.
        · The raw value is NEVER stored anywhere — not in DB, not in logs.
        · The hash is stored in IDVerification.id_number_hash (64-char hex).
        · Uniqueness of approved hashes is the permanent duplicate-account guard
          (checked by FraudRepository.get_verification_by_id_hash).

    BLAKE2b chosen over SHA-256 because:
        · Faster on 64-bit CPUs with no length-extension vulnerability.
        · 256-bit (digest_size=32) output is sufficient for a one-way hash
          on relatively short strings like government ID numbers.
    """
    normalised = raw_id.upper().strip().replace(" ", "")
    return hashlib.blake2b(normalised.encode(), digest_size=32).hexdigest()
