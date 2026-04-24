"""
api/v1/oauth.py — OAuth2 Authorization Server endpoints.

Supported flows:
  1. Authorization Code + PKCE  — for mini-apps / mobile / SPA
  2. Client Credentials          — for server-to-server (machine to machine)
  3. Refresh Token               — extended session for Authorization Code flow

OIDC Discovery + JWKS endpoints allow conformant SDK auto-configuration.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import jwt
import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    generate_opaque_token, hash_code,
    verify_client_secret,
)
from db.session import get_async_session
from models.integration import (
    IntegrationClient, OAuthAuthorizationCode, OAuthToken,
    TokenGrantType,
)

log = structlog.get_logger(__name__)
router = APIRouter(tags=["Integration — OAuth2"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method == "S256":
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return digest == code_challenge
    # plain (discouraged but spec-required)
    return code_verifier == code_challenge


def _issue_access_token(
    client: IntegrationClient,
    scopes: list[str],
    user_id: Optional[uuid.UUID] = None,
    grant_type: TokenGrantType = TokenGrantType.CLIENT_CREDENTIALS,
) -> tuple[str, str, datetime]:
    """Returns (access_token_jwt, jti, expires_at)."""
    jti = secrets.token_urlsafe(32)
    exp = datetime.utcnow() + timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS)
    payload = {
        "iss":       "https://riviwa.com",
        "sub":       str(user_id) if user_id else str(client.id),
        "aud":       client.client_id,
        "jti":       jti,
        "exp":       int(exp.timestamp()),
        "iat":       int(time.time()),
        "client_id": client.client_id,
        "scopes":    scopes,
        "env":       client.environment,
    }
    if user_id:
        payload["user_id"] = str(user_id)

    token = jwt.encode(payload, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM)
    return token, jti, exp


async def _store_token(
    db: AsyncSession,
    client: IntegrationClient,
    jti: str,
    scopes: list[str],
    expires_at: datetime,
    grant_type: TokenGrantType,
    user_id: Optional[uuid.UUID] = None,
    refresh_token_hash: Optional[str] = None,
    refresh_expires_at: Optional[datetime] = None,
) -> OAuthToken:
    row = OAuthToken(
        jti               = jti,
        client_id         = client.id,
        user_id           = user_id,
        grant_type        = grant_type,
        scopes            = scopes,
        refresh_token_hash = refresh_token_hash,
        refresh_expires_at = refresh_expires_at,
        expires_at        = expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ── GET /integration/oauth/authorize ─────────────────────────────────────────

@router.get("/integration/oauth/authorize")
async def authorize(
    request: Request,
    response_type:         str = "code",
    client_id:             str = "",
    redirect_uri:          str = "",
    scope:                 str = "feedback:write",
    state:                 Optional[str] = None,
    code_challenge:        str = "",
    code_challenge_method: str = "S256",
    db: AsyncSession = Depends(get_async_session),
):
    """
    Authorization endpoint.

    The partner's mobile app / SPA redirects the user here.
    After the user authenticates via Riviwa's login UI the server
    issues a short-lived authorization code and redirects back.

    NOTE: In the current implementation the endpoint returns a code
    immediately assuming the platform JWT in the X-Auth header already
    identifies the user. A full login widget is out of scope for v1.
    """
    if response_type != "code":
        raise HTTPException(400, {"error": "unsupported_response_type"})
    if not code_challenge:
        raise HTTPException(400, {"error": "code_challenge_required",
                                  "description": "PKCE is mandatory"})
    if code_challenge_method not in ("S256", "plain"):
        raise HTTPException(400, {"error": "invalid_code_challenge_method"})

    # Load and validate client
    result = await db.execute(
        select(IntegrationClient).where(
            IntegrationClient.client_id == client_id,
            IntegrationClient.is_active == True,
        )
    )
    client = result.scalars().first()
    if not client:
        raise HTTPException(400, {"error": "invalid_client"})
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(400, {"error": "invalid_redirect_uri"})

    # Validate requested scopes against client's allowed scopes
    requested = set(scope.split())
    invalid   = requested - set(client.allowed_scopes)
    if invalid:
        return RedirectResponse(
            redirect_uri + "?" + urlencode({
                "error": "invalid_scope",
                "state": state or "",
            })
        )

    # Extract user from Authorization header (Riviwa user JWT)
    user_id: Optional[uuid.UUID] = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                auth_header[7:], settings.AUTH_SECRET_KEY,
                algorithms=[settings.AUTH_ALGORITHM],
                options={"verify_aud": False},
            )
            user_id = uuid.UUID(payload["user_id"]) if payload.get("user_id") else None
        except Exception:
            pass

    # Generate authorization code
    raw_code   = secrets.token_urlsafe(32)
    code_hash  = hash_code(raw_code)
    expires_at = datetime.utcnow() + timedelta(seconds=settings.AUTH_CODE_TTL_SECONDS)

    auth_code = OAuthAuthorizationCode(
        client_id              = client.id,
        code_hash              = code_hash,
        redirect_uri           = redirect_uri,
        scopes                 = list(requested),
        code_challenge         = code_challenge,
        code_challenge_method  = code_challenge_method,
        user_id                = user_id,
        expires_at             = expires_at,
    )
    db.add(auth_code)
    await db.commit()

    log.info("oauth.code_issued", client_id=client.client_id)

    params = {"code": raw_code}
    if state:
        params["state"] = state
    return RedirectResponse(redirect_uri + "?" + urlencode(params),
                            status_code=302)


# ── POST /integration/oauth/token ─────────────────────────────────────────────

@router.post("/integration/oauth/token")
async def token_endpoint(
    request: Request,
    grant_type:    str = Form(...),
    # Authorization Code
    code:          Optional[str] = Form(None),
    redirect_uri:  Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    # Client Credentials / Auth Code — client identity
    client_id:     Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    # Refresh Token
    refresh_token: Optional[str] = Form(None),
    # Scope
    scope:         Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Token endpoint — supports three grant types:

    **authorization_code**
      Exchanges a PKCE authorization code for access + refresh tokens.
      Requires: code, redirect_uri, code_verifier, client_id.

    **client_credentials**
      Machine-to-machine. Returns access token only.
      Requires: client_id, client_secret. Uses HTTP Basic or form params.

    **refresh_token**
      Rotates refresh token. Returns new access + refresh token pair.
      Requires: refresh_token, client_id.
    """
    # ── Resolve client identity (Basic auth or form params) ────────────────
    cid, csecret = client_id, client_secret
    basic = request.headers.get("authorization", "")
    if basic.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(basic[6:]).decode()
            cid, csecret = decoded.split(":", 1)
        except Exception:
            raise HTTPException(401, {"error": "invalid_client"})

    if not cid:
        raise HTTPException(400, {"error": "invalid_request",
                                  "description": "client_id required"})

    result = await db.execute(
        select(IntegrationClient).where(
            IntegrationClient.client_id == cid,
            IntegrationClient.is_active == True,
        )
    )
    client = result.scalars().first()
    if not client:
        raise HTTPException(401, {"error": "invalid_client"})

    # ── Authorization Code grant ───────────────────────────────────────────
    if grant_type == "authorization_code":
        if not all([code, redirect_uri, code_verifier]):
            raise HTTPException(400, {"error": "invalid_request",
                                      "description": "code, redirect_uri, code_verifier required"})

        code_hash = hash_code(code)
        ac_result = await db.execute(
            select(OAuthAuthorizationCode).where(
                OAuthAuthorizationCode.code_hash  == code_hash,
                OAuthAuthorizationCode.client_id  == client.id,
                OAuthAuthorizationCode.used_at.is_(None),
            )
        )
        auth_code = ac_result.scalars().first()
        if not auth_code:
            raise HTTPException(400, {"error": "invalid_grant"})
        if auth_code.expires_at < datetime.utcnow():
            raise HTTPException(400, {"error": "invalid_grant", "description": "code expired"})
        if auth_code.redirect_uri != redirect_uri:
            raise HTTPException(400, {"error": "invalid_grant", "description": "redirect_uri mismatch"})
        if not _verify_pkce(code_verifier, auth_code.code_challenge,
                            auth_code.code_challenge_method):
            raise HTTPException(400, {"error": "invalid_grant", "description": "PKCE verification failed"})

        # Mark code as used
        auth_code.used_at = datetime.utcnow()
        await db.commit()

        access_token, jti, exp = _issue_access_token(
            client, auth_code.scopes, auth_code.user_id,
            TokenGrantType.AUTHORIZATION_CODE,
        )
        raw_refresh, refresh_hash = generate_opaque_token()
        refresh_exp = datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS)

        await _store_token(
            db, client, jti, auth_code.scopes, exp,
            TokenGrantType.AUTHORIZATION_CODE,
            user_id             = auth_code.user_id,
            refresh_token_hash  = refresh_hash,
            refresh_expires_at  = refresh_exp,
        )
        log.info("oauth.token_issued", grant="authorization_code", client=cid)
        return {
            "access_token":  access_token,
            "token_type":    "bearer",
            "expires_in":    settings.ACCESS_TOKEN_TTL_SECONDS,
            "refresh_token": raw_refresh,
            "scope":         " ".join(auth_code.scopes),
        }

    # ── Client Credentials grant ───────────────────────────────────────────
    elif grant_type == "client_credentials":
        if not csecret or not verify_client_secret(csecret, client.client_secret_hash):
            raise HTTPException(401, {"error": "invalid_client",
                                      "description": "invalid client_secret"})

        requested_scopes = scope.split() if scope else client.allowed_scopes
        invalid = set(requested_scopes) - set(client.allowed_scopes)
        if invalid:
            raise HTTPException(400, {"error": "invalid_scope"})

        access_token, jti, exp = _issue_access_token(
            client, requested_scopes, None, TokenGrantType.CLIENT_CREDENTIALS
        )
        await _store_token(db, client, jti, requested_scopes, exp,
                           TokenGrantType.CLIENT_CREDENTIALS)
        log.info("oauth.token_issued", grant="client_credentials", client=cid)
        return {
            "access_token": access_token,
            "token_type":   "bearer",
            "expires_in":   settings.ACCESS_TOKEN_TTL_SECONDS,
            "scope":        " ".join(requested_scopes),
        }

    # ── Refresh Token grant ────────────────────────────────────────────────
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(400, {"error": "invalid_request",
                                      "description": "refresh_token required"})

        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        rt_result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.refresh_token_hash == refresh_hash,
                OAuthToken.client_id          == client.id,
                OAuthToken.revoked_at.is_(None),
            )
        )
        old_token = rt_result.scalars().first()
        if not old_token:
            raise HTTPException(400, {"error": "invalid_grant"})
        if old_token.refresh_expires_at and old_token.refresh_expires_at < datetime.utcnow():
            raise HTTPException(400, {"error": "invalid_grant", "description": "refresh_token expired"})

        # Revoke old token (token rotation)
        old_token.revoked_at = datetime.utcnow()
        await db.commit()

        access_token, jti, exp = _issue_access_token(
            client, old_token.scopes, old_token.user_id,
            TokenGrantType.REFRESH_TOKEN,
        )
        raw_refresh, new_refresh_hash = generate_opaque_token()
        refresh_exp = datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS)

        await _store_token(
            db, client, jti, old_token.scopes, exp,
            TokenGrantType.REFRESH_TOKEN,
            user_id             = old_token.user_id,
            refresh_token_hash  = new_refresh_hash,
            refresh_expires_at  = refresh_exp,
        )
        log.info("oauth.token_refreshed", client=cid)
        return {
            "access_token":  access_token,
            "token_type":    "bearer",
            "expires_in":    settings.ACCESS_TOKEN_TTL_SECONDS,
            "refresh_token": raw_refresh,
            "scope":         " ".join(old_token.scopes),
        }

    raise HTTPException(400, {"error": "unsupported_grant_type"})


# ── POST /integration/oauth/revoke ────────────────────────────────────────────

@router.post("/integration/oauth/revoke", status_code=status.HTTP_200_OK)
async def revoke_token(
    token:         str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id:     Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Revoke an access token or refresh token (RFC 7009).
    Always returns 200 OK even if token is unknown (per spec).
    """
    # Try access token (JWT → JTI lookup)
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY,
                             algorithms=[settings.AUTH_ALGORITHM],
                             options={"verify_exp": False})
        jti = payload.get("jti")
        if jti:
            result = await db.execute(select(OAuthToken).where(OAuthToken.jti == jti))
            row = result.scalars().first()
            if row and not row.revoked_at:
                row.revoked_at = datetime.utcnow()
                await db.commit()
            return {"revoked": True}
    except Exception:
        pass

    # Try refresh token (opaque → hash lookup)
    refresh_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.refresh_token_hash == refresh_hash)
    )
    row = result.scalars().first()
    if row and not row.revoked_at:
        row.revoked_at = datetime.utcnow()
        await db.commit()

    return {"revoked": True}


# ── POST /integration/oauth/introspect ────────────────────────────────────────

@router.post("/integration/oauth/introspect")
async def introspect_token(
    token:           str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Token introspection (RFC 7662).
    Returns active=false for invalid/expired/revoked tokens.
    """
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY,
                             algorithms=[settings.AUTH_ALGORITHM],
                             options={"verify_aud": False})
    except jwt.ExpiredSignatureError:
        return {"active": False}
    except jwt.InvalidTokenError:
        return {"active": False}

    jti = payload.get("jti")
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.jti == jti,
            OAuthToken.revoked_at.is_(None),
        )
    )
    row = result.scalars().first()
    if not row:
        return {"active": False}

    return {
        "active":    True,
        "sub":       payload.get("sub"),
        "client_id": payload.get("client_id"),
        "scope":     " ".join(payload.get("scopes", [])),
        "exp":       payload.get("exp"),
        "iat":       payload.get("iat"),
        "jti":       jti,
    }


# ── GET /integration/oauth/userinfo ──────────────────────────────────────────

@router.get("/integration/oauth/userinfo")
async def userinfo(
    authorization: str = "",
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    OIDC userinfo endpoint.
    Returns basic profile for the authenticated user (requires profile:read scope).
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, {"error": "missing_token"})
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY,
                             algorithms=[settings.AUTH_ALGORITHM],
                             options={"verify_aud": False})
    except Exception:
        raise HTTPException(401, {"error": "invalid_token"})

    if "profile:read" not in payload.get("scopes", []):
        raise HTTPException(403, {"error": "insufficient_scope",
                                  "required": "profile:read"})

    user_id = payload.get("user_id") or payload.get("sub")
    return {
        "sub":        user_id,
        "client_id":  payload.get("client_id"),
        "scopes":     payload.get("scopes", []),
    }


# ── GET /.well-known/openid-configuration ─────────────────────────────────────

@router.get("/integration/.well-known/openid-configuration")
async def oidc_discovery(request: Request) -> dict:
    """OIDC Discovery document for automatic SDK configuration."""
    base = str(request.base_url).rstrip("/")
    return {
        "issuer":                                 "https://riviwa.com",
        "authorization_endpoint":                 f"{base}/api/v1/integration/oauth/authorize",
        "token_endpoint":                         f"{base}/api/v1/integration/oauth/token",
        "revocation_endpoint":                    f"{base}/api/v1/integration/oauth/revoke",
        "introspection_endpoint":                 f"{base}/api/v1/integration/oauth/introspect",
        "userinfo_endpoint":                      f"{base}/api/v1/integration/oauth/userinfo",
        "jwks_uri":                               f"{base}/api/v1/integration/.well-known/jwks.json",
        "response_types_supported":               ["code"],
        "grant_types_supported":                  ["authorization_code", "client_credentials", "refresh_token"],
        "token_endpoint_auth_methods_supported":  ["client_secret_basic", "client_secret_post"],
        "scopes_supported":                       ["feedback:write", "feedback:read", "profile:read", "data:push"],
        "code_challenge_methods_supported":       ["S256", "plain"],
        "subject_types_supported":                ["public"],
    }


# ── GET /.well-known/jwks.json ─────────────────────────────────────────────────

@router.get("/integration/.well-known/jwks.json")
async def jwks() -> dict:
    """
    JWKS endpoint.
    For HS256, there is no public key to publish.
    Returns an empty keys array — consuming SDKs should use client_secret verification
    or contact Riviwa to negotiate an RS256 keypair.
    """
    return {"keys": []}
