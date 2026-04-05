"""
services/geo_service.py
──────────────────────────────────────────────────────────────────
IP geolocation + VPN / Tor / datacenter detection.
Results are cached in Redis for 24 h to avoid hammering the API.

Provider: ip-api.com (free tier: 45 req/min).
  · Free tier maps both VPN and Tor to the single `proxy` field.
    is_tor will always be False on the free tier; only is_vpn is
    populated.  The risk_score property accounts for this correctly,
    but Tor users are underpenalised.  Upgrade to ip-api Pro or swap
    for IPQualityScore / MaxMind GeoIP2 for granular VPN/Tor signals.

Redis integration
──────────────────────────────────────────────────────────────────
lookup_ip() accepts an optional pre-constructed Redis client so that
callers using FastAPI dependency injection pass their request-scoped
client in.  When redis=None it falls back to the module-level
get_redis() singleton — convenient for standalone scripts, but
should be avoided in the main request path to keep Redis usage
testable and consistent with the rest of the service layer.
"""
from __future__ import annotations

import dataclasses
import ipaddress
import json
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog
from redis.asyncio import Redis

from core.config import settings

log = structlog.get_logger(__name__)

_CACHE_TTL    = 86_400          # 24 hours
_HTTPX_TIMEOUT = 3.0            # seconds; covers connect + read


@dataclass
class GeoResult:
    ip_address: str
    country_code: Optional[str]  = None
    region: Optional[str]        = None
    city: Optional[str]          = None
    latitude: Optional[float]    = None
    longitude: Optional[float]   = None
    isp: Optional[str]           = None
    asn: Optional[str]           = None
    is_vpn: bool                 = False
    is_tor: bool                 = False
    is_proxy: bool               = False
    is_datacenter: bool          = False
    is_high_risk_country: bool   = False
    lookup_failed: bool          = False

    @property
    def risk_score(self) -> int:
        """0-100 contribution to fraud score from this IP."""
        score = 0
        if self.is_tor:
            score += 40
        if self.is_vpn:
            score += 25
        if self.is_proxy:
            score += 20
        if self.is_datacenter:
            score += 15
        if self.is_high_risk_country:
            score += 20
        return min(score, 100)


async def lookup_ip(
    ip_address: str,
    redis: Optional[Redis] = None,
) -> GeoResult:
    """
    Look up geo + risk signals for an IP.

    Returns cached result when available (TTL 24 h).  On lookup failure
    (private IP, provider error, Redis unavailable) returns a safe
    GeoResult with lookup_failed=True and risk_score=0 so the caller
    is never blocked by an infrastructure fault.

    Args:
        ip_address: The address to look up.
        redis:      Optional pre-constructed Redis client.  When None,
                    falls back to the get_redis() singleton.  Pass the
                    request-scoped client from FastAPI DI in production.
    """
    if _is_private(ip_address):
        return GeoResult(ip_address=ip_address, lookup_failed=True)

    # Use the plain IP as the cache key — no hashing needed for a
    # non-sensitive, short string.
    cache_key = f"geo:{ip_address}"

    _redis = redis or await _get_fallback_redis()

    if _redis is not None:
        try:
            cached = await _redis.get(cache_key)
            if cached:
                return GeoResult(**json.loads(cached))
        except Exception as exc:
            log.warning("geo_service.redis_read_error", ip=ip_address, error=str(exc))

    result = await _fetch_from_provider(ip_address)

    if _redis is not None:
        try:
            # dataclasses.asdict() is safe for all primitive field types;
            # __dict__ can silently break if a field holds a non-serialisable value.
            await _redis.setex(cache_key, _CACHE_TTL, json.dumps(dataclasses.asdict(result)))
        except Exception as exc:
            log.warning("geo_service.redis_write_error", ip=ip_address, error=str(exc))

    return result


# ── Provider dispatch ──────────────────────────────────────────────────────────

async def _fetch_from_provider(ip_address: str) -> GeoResult:
    provider = getattr(settings, "GEOIP_PROVIDER", "ip-api").lower()
    if provider == "ip-api":
        return await _fetch_ip_api(ip_address)
    # Add MaxMind, ipinfo, IPQualityScore here
    log.warning("geo_service.unknown_provider", provider=provider)
    return GeoResult(ip_address=ip_address, lookup_failed=True)


async def _fetch_ip_api(ip_address: str) -> GeoResult:
    """
    ip-api.com free tier.  Fields param minimises response payload.
    Switch to ip-api.com/batch for bulk lookups.

    Free-tier limitation: the `proxy` field covers both VPN and Tor.
    is_vpn and is_tor both map to the same boolean; is_tor is always
    False on this tier.  Upgrade to ip-api Pro for separate signals.
    """
    url = (
        f"http://ip-api.com/json/{ip_address}"
        "?fields=status,message,countryCode,regionName,city,"
        "lat,lon,isp,as,proxy,hosting,query"
    )
    try:
        async with httpx.AsyncClient(timeout=_HTTPX_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "success":
            log.warning(
                "geo_service.ip_api_non_success",
                ip=ip_address,
                message=data.get("message"),
            )
            return GeoResult(ip_address=ip_address, lookup_failed=True)

        country = data.get("countryCode", "") or ""
        vpn_detection_enabled = getattr(settings, "VPN_DETECTION_ENABLED", True)
        high_risk_list = getattr(settings, "high_risk_country_list", set())
        is_high_risk = (
            vpn_detection_enabled and bool(country) and country in high_risk_list
        )
        is_proxy_or_vpn = bool(data.get("proxy", False))

        return GeoResult(
            ip_address=ip_address,
            country_code=country or None,
            region=data.get("regionName"),
            city=data.get("city"),
            latitude=data.get("lat"),
            longitude=data.get("lon"),
            isp=data.get("isp"),
            asn=data.get("as"),
            is_proxy=is_proxy_or_vpn,
            is_datacenter=bool(data.get("hosting", False)),
            # Free tier: both VPN and Tor are reported via proxy=true.
            # is_tor stays False until a Pro / dedicated Tor-detection feed is added.
            is_vpn=is_proxy_or_vpn,
            is_tor=False,
            is_high_risk_country=is_high_risk,
        )
    except httpx.HTTPError as exc:
        log.error("geo_service.http_error", ip=ip_address, error=str(exc))
        return GeoResult(ip_address=ip_address, lookup_failed=True)
    except Exception as exc:
        log.error("geo_service.lookup_exception", ip=ip_address, error=str(exc))
        return GeoResult(ip_address=ip_address, lookup_failed=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


async def _get_fallback_redis() -> Optional[Redis]:
    """
    Singleton fallback for non-DI callers (scripts, CLI tools).
    Returns None silently on failure so the caller can proceed without cache.
    """
    try:
        from db.session import get_redis_client as get_redis
        return await get_redis()
    except Exception as exc:
        log.warning("geo_service.redis_singleton_unavailable", error=str(exc))
        return None
