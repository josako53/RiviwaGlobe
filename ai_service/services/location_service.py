"""
services/location_service.py — Global location resolution for Riviwa AI.

Provides:
  - Reverse geocoding: (lat, lng) → structured address
  - Forward geocoding: text mention → (lat, lng) + structured address
  - Nearest branch lookup: (lat, lng) → closest OrgLocation within radius
  - Address normalization: Nominatim response → Riviwa standard fields

Backend: Nominatim (OpenStreetMap) — no API key required, global coverage.
Cache:   Redis (24h TTL for geocode results, 1h for branch lookups).
Rate limiting: 1 req/sec to Nominatim public API (OSM policy).

Country-specific address fields are stored in address_components JSONB:
  TZ:  {"district": "Ilala", "lga": "Ilala MC", "ward": "Upanga West", "mtaa": "Upanga Mjini"}
  UK:  {"county": "Greater London", "city_district": "London Borough of Hackney"}
  USA: {"county": "Travis County", "neighbourhood": "Hyde Park"}
  KE:  {"county": "Nairobi County", "sub_county": "Westlands", "ward": "Parklands"}
"""
from __future__ import annotations

import asyncio
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

# ── Nominatim config ──────────────────────────────────────────────────────────
_NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
# OSM policy: must identify your application in User-Agent
_USER_AGENT = "Riviwa/1.0 (contact@riviwa.com; https://riviwa.com)"
# Rate limit: 1 request/sec per OSM fair-use policy
_RATE_LIMIT_SECS = 1.1
_last_request_time: float = 0.0
_rate_lock = asyncio.Lock()

# Redis key prefixes
_CACHE_FWD   = "geo:fwd:"   # forward geocode: text → location
_CACHE_REV   = "geo:rev:"   # reverse geocode: "lat,lng" → location
_CACHE_NEAR  = "geo:near:"  # nearest branch: "lat,lng,org_id" → branch_id
_CACHE_TTL   = 86_400       # 24 hours for geocode results
_BRANCH_TTL  = 3_600        # 1 hour for nearest-branch results

# Earth radius in km (WGS-84 mean radius)
_EARTH_KM = 6_371.0


# ── Redis helper ──────────────────────────────────────────────────────────────

def _get_redis():
    """Return a Redis client using the auth service Redis DB 4 for location cache."""
    try:
        import redis
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_LOCATION_DB,
            decode_responses=True,
        )
    except Exception:
        return None


def _cache_get(key: str) -> Optional[dict]:
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key: str, value: dict, ttl: int) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


# ── Rate-limited Nominatim request ───────────────────────────────────────────

async def _nominatim_get(path: str, params: dict) -> Optional[dict]:
    """
    Rate-limited GET to Nominatim. Returns parsed JSON or None on error.
    Enforces OSM's 1 req/sec fair-use policy globally across all callers.
    """
    global _last_request_time

    async with _rate_lock:
        now = asyncio.get_event_loop().time()
        wait = _RATE_LIMIT_SECS - (now - _last_request_time)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_time = asyncio.get_event_loop().time()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{_NOMINATIM_BASE}{path}",
                params={**params, "format": "json", "addressdetails": 1},
                headers={"User-Agent": _USER_AGENT, "Accept-Language": "en"},
            )
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("location.nominatim_error", path=path, error=str(exc))
        return None


# ── Address normalization ─────────────────────────────────────────────────────

def normalize_address(raw: dict) -> dict:
    """
    Convert a Nominatim address dict into Riviwa's standard location structure.

    Standard fields (populated for all countries):
      city, region, suburb, postal_code, country_code, display_name,
      latitude, longitude, source, address_components, osm_id, osm_type, place_id

    address_components holds ALL country-specific extra fields:
      TZ → district, lga, ward, mtaa
      UK → county, city_district
      USA → county, neighbourhood, state_district
      KE → county, sub_county, ward
      IN → state_district, suburb
    """
    addr = raw.get("address", {})
    cc = addr.get("country_code", "").lower()

    # ── Standard fields (global) ──────────────────────────────────────────────
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or ""
    )
    region = (
        addr.get("state")
        or addr.get("province")
        or addr.get("region")
        or ""
    )
    suburb = (
        addr.get("suburb")
        or addr.get("neighbourhood")
        or addr.get("quarter")
        or addr.get("estate")
        or addr.get("residential")
        or ""
    )
    postal_code = addr.get("postcode") or addr.get("postal_code") or ""

    # ── Country-specific components (stored in JSONB) ─────────────────────────
    components: Dict[str, Any] = {}

    # Fields that are country-specific and don't have a standard column
    _component_keys = [
        # Administrative hierarchy
        "county", "district", "city_district", "state_district",
        # Sub-administrative
        "sub_county", "ward", "lga", "mtaa",
        # Locality
        "neighbourhood", "quarter", "estate", "residential", "allotments",
        # Transport/address
        "road", "house_number", "amenity", "building",
        # OSM categories
        "industrial", "retail", "commercial",
    ]
    for key in _component_keys:
        if addr.get(key):
            components[key] = addr[key]

    # Keep original full address dict for reference (without standard fields)
    _skip = {"country_code", "country", "city", "town", "village", "municipality",
              "state", "province", "region", "suburb", "postcode", "postal_code"}
    for k, v in addr.items():
        if k not in _skip and k not in components and v:
            components[k] = v

    return {
        "city":               city,
        "region":             region,
        "suburb":             suburb or None,
        "postal_code":        postal_code or None,
        "country_code":       cc.upper() if cc else "",
        "display_name":       raw.get("display_name", ""),
        "latitude":           float(raw.get("lat", 0)) if raw.get("lat") else None,
        "longitude":          float(raw.get("lon", 0)) if raw.get("lon") else None,
        "source":             "osm",
        "address_components": components if components else None,
        "osm_id":             int(raw.get("osm_id", 0)) if raw.get("osm_id") else None,
        "osm_type":           raw.get("osm_type"),
        "place_id":           int(raw.get("place_id", 0)) if raw.get("place_id") else None,
    }


# ── Forward geocoding ─────────────────────────────────────────────────────────

async def forward_geocode(text: str, country_codes: Optional[List[str]] = None) -> Optional[dict]:
    """
    Convert a location text mention to coordinates + structured address.

    Args:
        text: Free-text location e.g. "Kariakoo, Dar es Salaam" or "Hyde Park, London"
        country_codes: Optional list of ISO 3166-1 alpha-2 codes to bias results
                       e.g. ["TZ", "KE"] for East Africa focus

    Returns:
        Normalized address dict or None if not found.
    """
    cache_key = _CACHE_FWD + text.lower().strip()[:200]
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict = {"q": text, "limit": 1}
    if country_codes:
        params["countrycodes"] = ",".join(c.lower() for c in country_codes)

    raw = await _nominatim_get("/search", params)
    if not raw or not isinstance(raw, list) or len(raw) == 0:
        log.debug("location.forward_geocode_no_result", text=text)
        return None

    result = normalize_address(raw[0])
    _cache_set(cache_key, result, _CACHE_TTL)
    log.debug("location.forward_geocode", text=text, lat=result.get("latitude"), lng=result.get("longitude"))
    return result


# ── Reverse geocoding ─────────────────────────────────────────────────────────

async def reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    """
    Convert GPS coordinates to a structured address.

    Returns normalized address dict or None on failure.
    """
    cache_key = _CACHE_REV + f"{lat:.5f},{lng:.5f}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    raw = await _nominatim_get("/reverse", {"lat": lat, "lon": lng, "zoom": 18})
    if not raw or "error" in raw:
        log.debug("location.reverse_geocode_failed", lat=lat, lng=lng)
        return None

    result = normalize_address(raw)
    result["latitude"]  = lat
    result["longitude"] = lng
    _cache_set(cache_key, result, _CACHE_TTL)
    log.debug("location.reverse_geocode", lat=lat, lng=lng, display=result.get("display_name", "")[:80])
    return result


# ── Haversine distance ────────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Return the great-circle distance in kilometres between two points.
    Pure math — no external dependency.
    """
    r = _EARTH_KM
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lng2 - lng1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


# ── Nearest branch lookup ─────────────────────────────────────────────────────

async def find_nearest_branch(
    lat: float,
    lng: float,
    org_id: Optional[str] = None,
    radius_km: float = 2.0,
) -> Optional[dict]:
    """
    Find the nearest OrgBranch (via OrgLocation) within radius_km of the given point.

    Calls the auth service's internal location search endpoint which returns
    branch locations sorted by distance. Falls back to None if auth service
    is unreachable or no branch is within the radius.

    Returns:
        {branch_id, org_id, distance_km, display_name, city, region, ...}
    """
    cache_key = _CACHE_NEAR + f"{lat:.4f},{lng:.4f},{org_id or 'any'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict = {"lat": lat, "lng": lng, "radius_km": radius_km}
    if org_id:
        params["org_id"] = org_id

    _internal = {
        "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
        "X-Service-Name": "ai_service",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/locations/nearest",
                params=params,
                headers=_internal,
            )
            if r.status_code != 200:
                log.debug("location.nearest_branch_not_found", lat=lat, lng=lng, status=r.status_code)
                return None
            data = r.json()
    except Exception as exc:
        log.warning("location.nearest_branch_error", lat=lat, lng=lng, error=str(exc))
        return None

    if not data:
        return None

    # Pick the closest result and compute exact Haversine distance
    item = data[0] if isinstance(data, list) else data
    b_lat = item.get("latitude")
    b_lng = item.get("longitude")
    if b_lat and b_lng:
        item["distance_km"] = round(haversine_km(lat, lng, float(b_lat), float(b_lng)), 3)
    else:
        item["distance_km"] = None

    if item.get("distance_km") and item["distance_km"] > radius_km:
        return None

    _cache_set(cache_key, item, _BRANCH_TTL)
    log.info("location.nearest_branch_found",
             branch_id=item.get("branch_id"),
             distance_km=item.get("distance_km"))
    return item


# ── GPS + text combined resolution ───────────────────────────────────────────

async def resolve_location(
    gps_lat: Optional[float] = None,
    gps_lng: Optional[float] = None,
    location_text: Optional[str] = None,
    org_id: Optional[str] = None,
    country_hint: Optional[List[str]] = None,
) -> dict:
    """
    Main entry point. Resolves location from GPS and/or text mention.

    Priority:
      1. GPS coordinates (most precise) → reverse geocode + nearest branch
      2. Text mention → forward geocode → nearest branch

    Returns:
        {
          "latitude": float|None,
          "longitude": float|None,
          "display_name": str|None,
          "city": str|None,
          "region": str|None,
          "suburb": str|None,
          "country_code": str|None,
          "postal_code": str|None,
          "address_components": dict|None,    # ward/lga/county/etc.
          "branch_id": str|None,              # nearest resolved branch UUID
          "branch_distance_km": float|None,
          "source": "gps"|"osm"|"text"|None,
        }
    """
    result: dict = {
        "latitude":           None,
        "longitude":          None,
        "display_name":       None,
        "city":               None,
        "region":             None,
        "suburb":             None,
        "country_code":       None,
        "postal_code":        None,
        "address_components": None,
        "branch_id":          None,
        "branch_distance_km": None,
        "source":             None,
    }

    lat, lng = None, None

    # ── Mode 1: GPS ───────────────────────────────────────────────────────────
    if gps_lat is not None and gps_lng is not None:
        geo = await reverse_geocode(gps_lat, gps_lng)
        if geo:
            result.update(geo)
            result["source"]    = "gps"
            result["latitude"]  = gps_lat
            result["longitude"] = gps_lng
        lat, lng = gps_lat, gps_lng

    # ── Mode 2: Text mention (fallback or supplement) ─────────────────────────
    elif location_text:
        geo = await forward_geocode(location_text, country_codes=country_hint)
        if geo:
            result.update(geo)
            result["source"] = "text"
            lat = geo.get("latitude")
            lng = geo.get("longitude")

    # ── Nearest branch lookup ─────────────────────────────────────────────────
    if lat and lng:
        branch = await find_nearest_branch(lat, lng, org_id=org_id)
        if branch:
            result["branch_id"]          = branch.get("branch_id")
            result["branch_distance_km"] = branch.get("distance_km")

    return result
