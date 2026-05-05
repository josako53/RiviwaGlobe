from __future__ import annotations
from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from core.config import settings


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


JWTDep = Depends(_require_jwt)
