"""
api/v1/clients.py — Partner client registration and API key management.

All endpoints require platform admin JWT (from auth_service).
Partners are registered here before they can use any other integration endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    generate_api_key, generate_client_credentials,
    generate_webhook_signing_secret,
)
from db.session import get_async_session
from models.integration import ApiKey, IntegrationClient, ClientType, ClientEnvironment

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/clients", tags=["Integration — Client Management"])


def _require_platform_admin(authorization: str = Header(...)):
    """Verify the caller is a Riviwa platform admin (super_admin role)."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "MISSING_TOKEN"})
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY,
                             algorithms=[settings.AUTH_ALGORITHM],
                             options={"verify_aud": False})
        if payload.get("platform_role") not in ("super_admin", "admin"):
            raise HTTPException(status_code=403, detail={"error": "INSUFFICIENT_ROLE"})
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"error": "TOKEN_EXPIRED"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"error": "INVALID_TOKEN"})


AdminDep = Depends(_require_platform_admin)


# ── POST /integration/clients — Register new partner ─────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def register_client(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    """
    Register a new integration partner.
    Returns client_id and client_secret (shown ONCE — store securely).
    """
    client_id, client_secret, secret_hash = generate_client_credentials()

    # Webhook signing secret (shown once if webhook_url provided)
    webhook_raw, webhook_hash = (None, None)
    if body.get("webhook_url"):
        webhook_raw, webhook_hash = generate_webhook_signing_secret()

    client = IntegrationClient(
        client_id           = client_id,
        client_secret_hash  = secret_hash,
        name                = body["name"],
        description         = body.get("description"),
        client_type         = ClientType(body.get("client_type", "API")),
        environment         = ClientEnvironment(body.get("environment", "SANDBOX")),
        organisation_id     = uuid.UUID(body["organisation_id"]) if body.get("organisation_id") else None,
        allowed_scopes      = body.get("allowed_scopes", ["feedback:write"]),
        allowed_origins     = body.get("allowed_origins", []),
        allowed_ips         = body.get("allowed_ips", []),
        redirect_uris       = body.get("redirect_uris", []),
        webhook_url         = body.get("webhook_url"),
        webhook_secret_hash = webhook_hash,
        webhook_events      = body.get("webhook_events", []),
        data_endpoint_url   = body.get("data_endpoint_url"),
        require_mtls        = body.get("require_mtls", False),
        rate_limit_per_minute = body.get("rate_limit_per_minute", settings.DEFAULT_RATE_LIMIT_PER_MINUTE),
        rate_limit_per_day    = body.get("rate_limit_per_day", settings.DEFAULT_RATE_LIMIT_PER_DAY),
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    log.info("integration.client_registered", client_id=client_id, name=body["name"])

    response = {
        "id":            str(client.id),
        "client_id":     client.client_id,
        "client_secret": client_secret,   # shown ONCE
        "name":          client.name,
        "client_type":   client.client_type,
        "environment":   client.environment,
        "allowed_scopes": client.allowed_scopes,
        "created_at":    client.created_at.isoformat(),
        "warning":       "Store client_secret securely — it will not be shown again.",
    }
    if webhook_raw:
        response["webhook_signing_secret"] = webhook_raw
        response["webhook_warning"] = "Store webhook_signing_secret securely — it will not be shown again."

    return response


# ── GET /integration/clients/{id} — Get client ───────────────────────────────

@router.get("/{client_uuid}")
async def get_client(
    client_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    client = await db.get(IntegrationClient, client_uuid)
    if not client:
        raise HTTPException(status_code=404, detail={"error": "CLIENT_NOT_FOUND"})
    return _client_out(client)


# ── GET /integration/clients — List clients ───────────────────────────────────

@router.get("")
async def list_clients(
    environment: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    q = select(IntegrationClient).where(IntegrationClient.is_active == True)
    if environment:
        q = q.where(IntegrationClient.environment == environment.upper())
    rows = (await db.execute(q.order_by(IntegrationClient.created_at.desc()))).scalars().all()
    return {"total": len(rows), "items": [_client_out(c) for c in rows]}


# ── PATCH /integration/clients/{id} — Update client ──────────────────────────

@router.patch("/{client_uuid}")
async def update_client(
    client_uuid: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    client = await db.get(IntegrationClient, client_uuid)
    if not client:
        raise HTTPException(status_code=404, detail={"error": "CLIENT_NOT_FOUND"})

    updatable = [
        "name", "description", "allowed_scopes", "allowed_origins",
        "allowed_ips", "redirect_uris", "webhook_url", "webhook_events",
        "data_endpoint_url", "rate_limit_per_minute", "rate_limit_per_day",
        "require_mtls", "mtls_cert_fingerprint",
    ]
    for field in updatable:
        if field in body:
            setattr(client, field, body[field])
    client.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(client)
    return _client_out(client)


# ── DELETE /integration/clients/{id} — Deactivate ────────────────────────────

@router.delete("/{client_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_client(
    client_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
):
    client = await db.get(IntegrationClient, client_uuid)
    if not client:
        raise HTTPException(status_code=404, detail={"error": "CLIENT_NOT_FOUND"})
    client.is_active  = False
    client.updated_at = datetime.utcnow()
    await db.commit()
    log.info("integration.client_deactivated", client_id=client.client_id)


# ── POST /integration/clients/{id}/rotate-secret ─────────────────────────────

@router.post("/{client_uuid}/rotate-secret")
async def rotate_secret(
    client_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    """Rotate client_secret. Returns new secret (shown ONCE)."""
    client = await db.get(IntegrationClient, client_uuid)
    if not client:
        raise HTTPException(status_code=404, detail={"error": "CLIENT_NOT_FOUND"})

    import bcrypt
    new_secret = f"rwi_secret_{__import__('secrets').token_urlsafe(32)}"
    client.client_secret_hash = bcrypt.hashpw(new_secret.encode(), bcrypt.gensalt(12)).decode()
    client.updated_at = datetime.utcnow()
    await db.commit()
    return {"client_secret": new_secret,
            "warning": "Store this securely — it will not be shown again."}


# ── POST /integration/clients/{id}/api-keys — Issue API key ──────────────────

@router.post("/{client_uuid}/api-keys", status_code=status.HTTP_201_CREATED)
async def issue_api_key(
    client_uuid: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    client = await db.get(IntegrationClient, client_uuid)
    if not client:
        raise HTTPException(status_code=404, detail={"error": "CLIENT_NOT_FOUND"})

    scopes = body.get("scopes", client.allowed_scopes)
    invalid = set(scopes) - set(client.allowed_scopes)
    if invalid:
        raise HTTPException(status_code=400,
                            detail={"error": "INVALID_SCOPES", "invalid": list(invalid)})

    full_key, prefix, key_hash = generate_api_key(client.environment)
    expires_days = body.get("expires_days")
    expires_at   = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None

    api_key = ApiKey(
        client_id  = client.id,
        key_prefix = prefix,
        key_hash   = key_hash,
        name       = body.get("name"),
        scopes     = scopes,
        expires_at = expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    log.info("integration.api_key_issued", client_id=client.client_id, prefix=prefix)

    return {
        "id":       str(api_key.id),
        "api_key":  full_key,         # shown ONCE
        "prefix":   prefix,
        "scopes":   scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "warning":  "Store API key securely — it will not be shown again.",
    }


# ── DELETE /integration/clients/{id}/api-keys/{key_id} — Revoke key ──────────

@router.delete("/{client_uuid}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    client_uuid: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
):
    key = await db.get(ApiKey, key_id)
    if not key or key.client_id != client_uuid:
        raise HTTPException(status_code=404, detail={"error": "KEY_NOT_FOUND"})
    key.is_active  = False
    key.revoked_at = datetime.utcnow()
    await db.commit()
    log.info("integration.api_key_revoked", key_id=str(key_id), prefix=key.key_prefix)


# ── GET /integration/clients/{id}/api-keys — List keys ───────────────────────

@router.get("/{client_uuid}/api-keys")
async def list_api_keys(
    client_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _admin = AdminDep,
) -> dict:
    rows = (await db.execute(
        select(ApiKey)
        .where(ApiKey.client_id == client_uuid)
        .order_by(ApiKey.created_at.desc())
    )).scalars().all()
    return {
        "total": len(rows),
        "items": [
            {
                "id":          str(k.id),
                "prefix":      k.key_prefix,
                "name":        k.name,
                "scopes":      k.scopes,
                "is_active":   k.is_active,
                "expires_at":  k.expires_at.isoformat() if k.expires_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at":  k.created_at.isoformat(),
            }
            for k in rows
        ],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_out(c: IntegrationClient) -> dict:
    return {
        "id":             str(c.id),
        "client_id":      c.client_id,
        "name":           c.name,
        "description":    c.description,
        "client_type":    c.client_type,
        "environment":    c.environment,
        "organisation_id": str(c.organisation_id) if c.organisation_id else None,
        "allowed_scopes": c.allowed_scopes,
        "allowed_origins": c.allowed_origins,
        "allowed_ips":    c.allowed_ips,
        "redirect_uris":  c.redirect_uris,
        "webhook_url":    c.webhook_url,
        "webhook_events": c.webhook_events,
        "data_endpoint_url": c.data_endpoint_url,
        "require_mtls":   c.require_mtls,
        "rate_limit_per_minute": c.rate_limit_per_minute,
        "rate_limit_per_day":    c.rate_limit_per_day,
        "is_active":      c.is_active,
        "created_at":     c.created_at.isoformat(),
        "last_used_at":   c.last_used_at.isoformat() if c.last_used_at else None,
    }
