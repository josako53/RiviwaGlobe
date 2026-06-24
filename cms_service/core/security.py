from __future__ import annotations
from typing import Any, Optional
import structlog
from jose import JWTError, jwt
from core.config import settings

log = structlog.get_logger(__name__)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
    except JWTError as exc:
        log.debug("cms.jwt_decode_failed", error=str(exc))
        return None
