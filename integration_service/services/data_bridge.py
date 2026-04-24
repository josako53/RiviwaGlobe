"""
services/data_bridge.py — External data bridge (pull mode).

When a partner registers a data_endpoint_url, Riviwa fetches user context
from that endpoint on-demand (e.g., when a user starts a feedback session).

The partner's endpoint is called with the user's phone number or account_ref
and returns structured data: { name, service_id, product_id, category, ... }

Security:
  - Credentials stored AES-256-GCM encrypted in IntegrationClient.data_endpoint_auth_enc
  - Supported auth types: bearer | basic | api_key
  - 5-second timeout, single attempt (no retry — best-effort enrichment)
"""
from __future__ import annotations

import json
from typing import Optional

import httpx
import structlog

from core.config import settings
from core.security import decrypt_field
from models.integration import IntegrationClient

log = structlog.get_logger(__name__)


async def fetch_external_context(
    client: IntegrationClient,
    lookup_key: str,
    lookup_type: str = "phone",
) -> Optional[dict]:
    """
    Call the partner's data endpoint to retrieve user context.

    Args:
      client      — IntegrationClient with data_endpoint_url configured
      lookup_key  — phone number or account_ref to look up
      lookup_type — "phone" | "account_ref" | "email"

    Returns dict of pre-fill fields or None on any error.
    """
    if not client.data_endpoint_url:
        return None

    # Build auth header
    auth_headers: dict[str, str] = {}
    if client.data_endpoint_auth_type and client.data_endpoint_auth_enc:
        try:
            cred = decrypt_field(client.data_endpoint_auth_enc)
        except Exception:
            log.warning("data_bridge.decrypt_failed", client_id=str(client.id))
            return None

        if client.data_endpoint_auth_type == "bearer":
            auth_headers["Authorization"] = f"Bearer {cred}"
        elif client.data_endpoint_auth_type == "basic":
            auth_headers["Authorization"] = f"Basic {cred}"
        elif client.data_endpoint_auth_type == "api_key":
            auth_headers["X-API-Key"] = cred

    params = {lookup_type: lookup_key}

    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(
                client.data_endpoint_url,
                params=params,
                headers={**auth_headers, "Accept": "application/json"},
            )
        if resp.status_code != 200:
            log.warning("data_bridge.non_200",
                        client_id=str(client.id),
                        status=resp.status_code)
            return None
        data = resp.json()
        log.info("data_bridge.fetched",
                 client_id=str(client.id), lookup_type=lookup_type)
        return _normalize(data)
    except Exception as exc:
        log.warning("data_bridge.fetch_failed", client_id=str(client.id), error=str(exc))
        return None


def _normalize(raw: dict) -> dict:
    """
    Normalize partner response to Riviwa pre-fill field names.
    Partners may use different key names; map common variants.
    """
    mappings = {
        "phone_number": "phone",
        "mobile":       "phone",
        "msisdn":       "phone",
        "full_name":    "name",
        "customer_name": "name",
        "email_address": "email",
        "service":      "service_id",
        "product":      "product_id",
        "category":     "category_id",
        "account":      "account_ref",
        "account_number": "account_ref",
        "customer_id":  "account_ref",
    }
    out = {}
    for k, v in raw.items():
        canonical = mappings.get(k.lower(), k)
        out[canonical] = v
    return out
