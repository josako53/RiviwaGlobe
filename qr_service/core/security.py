from __future__ import annotations
import hashlib
import secrets
from core.config import settings


def generate_short_code(length: int = 8) -> str:
    chars = settings.SHORT_CODE_CHARS
    return "".join(secrets.choice(chars) for _ in range(length))


def fingerprint(ip: str, ua: str) -> str:
    return hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:16]
