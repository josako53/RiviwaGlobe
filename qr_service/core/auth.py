from __future__ import annotations
from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from core.config import settings


def _require_internal(x_service_key: str = Header(default="")):
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})


def _require_jwt(authorization: str = Header(default="")):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "MISSING_TOKEN"})
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail={"error": "INVALID_TOKEN"})


InternalDep = Depends(_require_internal)
JWTDep      = Depends(_require_jwt)
