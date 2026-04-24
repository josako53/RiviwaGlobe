"""
core/security.py — Cryptographic helpers for integration_service.

API Key format:   rwi_<env>_<48 random bytes base64url>
                  e.g. rwi_live_abc123...   rwi_sandbox_xyz789...
                  Stored as: prefix (first 12 chars) + SHA-256 hash

Client secrets:   bcrypt hash, shown ONCE at creation

Webhook signing:  HMAC-SHA256(body_bytes, raw_secret)
                  Header: X-Riviwa-Signature: sha256=<hex_digest>
                          X-Riviwa-Timestamp: <unix_ts>

At-rest encryption: AES-256-GCM via cryptography.fernet (key from settings.ENCRYPTION_KEY)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Tuple

import bcrypt
from cryptography.fernet import Fernet

from core.config import settings


# ── API Key management ────────────────────────────────────────────────────────

_ENV_TAG = {"LIVE": "live", "SANDBOX": "sandbox"}


def generate_api_key(environment: str = "SANDBOX") -> Tuple[str, str, str]:
    """
    Generate a new API key.
    Returns (full_key, prefix, sha256_hash).
    full_key is shown once to the client and never stored.
    """
    env_tag = _ENV_TAG.get(environment, "sandbox")
    random_part = secrets.token_urlsafe(36)   # 48 chars of base64url
    full_key = f"rwi_{env_tag}_{random_part}"
    prefix   = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode()).hexdigest()


def verify_api_key(full_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(full_key.encode()).hexdigest(),
        stored_hash,
    )


# ── Client secret management ──────────────────────────────────────────────────

def generate_client_credentials() -> Tuple[str, str, str]:
    """
    Generate (client_id, client_secret, client_secret_hash).
    client_secret is shown once and never stored.
    """
    client_id     = f"rwi_client_{secrets.token_urlsafe(16)}"
    client_secret = f"rwi_secret_{secrets.token_urlsafe(32)}"
    secret_hash   = bcrypt.hashpw(client_secret.encode(), bcrypt.gensalt(rounds=12)).decode()
    return client_id, client_secret, secret_hash


def verify_client_secret(secret: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(secret.encode(), stored_hash.encode())
    except Exception:
        return False


# ── Webhook signing ───────────────────────────────────────────────────────────

def generate_webhook_signing_secret() -> Tuple[str, str]:
    """
    Generate (raw_secret, bcrypt_hash).
    raw_secret is given to the partner for signature verification.
    """
    raw = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=12)).decode()
    return raw, hashed


def sign_webhook_payload(body_bytes: bytes, raw_secret: str) -> Tuple[str, str]:
    """
    Returns (signature, timestamp_str).
    Partner verifies: HMAC-SHA256(timestamp + '.' + body, secret)
    """
    ts  = str(int(time.time()))
    msg = f"{ts}.".encode() + body_bytes
    sig = hmac.new(raw_secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"sha256={sig}", ts


def verify_webhook_signature(
    body_bytes: bytes,
    raw_secret: str,
    signature_header: str,
    timestamp_header: str,
    tolerance_secs: int = 300,
) -> bool:
    """
    Verify an inbound webhook from a partner (for reverse webhooks).
    Rejects replays older than tolerance_secs.
    """
    try:
        ts = int(timestamp_header)
        if abs(time.time() - ts) > tolerance_secs:
            return False
        msg = f"{ts}.".encode() + body_bytes
        expected = "sha256=" + hmac.new(raw_secret.encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)
    except Exception:
        return False


# ── At-rest encryption (AES-256-GCM via Fernet) ───────────────────────────────

def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    # Fernet requires a 32-byte base64url key
    if len(key) < 32:
        raise ValueError("ENCRYPTION_KEY must be a 32-byte base64url string")
    # Ensure proper padding
    try:
        raw = base64.urlsafe_b64decode(key + "==")
        if len(raw) != 32:
            raise ValueError
        return Fernet(base64.urlsafe_b64encode(raw))
    except Exception:
        # Fallback: use key as-is if it's already proper Fernet format
        return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_field(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── Token generation helper ───────────────────────────────────────────────────

def generate_opaque_token(n_bytes: int = 32) -> Tuple[str, str]:
    """
    Generate (raw_token, sha256_hash) for refresh tokens / session tokens.
    raw_token is returned to the client; hash is stored.
    """
    raw  = secrets.token_urlsafe(n_bytes)
    hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hash


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
