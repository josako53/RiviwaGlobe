"""
services/address_service.py
═══════════════════════════════════════════════════════════════════════════════
Business logic for the Address resource, including Nominatim (OSM) integration.

Nominatim usage policy
───────────────────────
  · Base URL: https://nominatim.openstreetmap.org
  · Requires a descriptive User-Agent (ToS). Set via NOMINATIM_USER_AGENT.
  · Public API: max 1 request/second. For production traffic consider
    self-hosting Nominatim or using a commercial geocoding provider.
  · Results are NOT cached here. Add Redis caching in front of
    _nominatim_get() if QPS becomes a concern.

Tanzania hierarchy mapping (Nominatim → Address fields)
────────────────────────────────────────────────────────
  Nominatim field          → Address field
  ──────────────────────── → ──────────────
  address.state            → region
  address.state_district   → district  (fallback: address.county)
  address.county           → lga
  address.suburb           → ward       (fallback: city_district)
  address.quarter          → mtaa       (fallback: neighbourhood)
  address.city / town / village / municipality → city
  address.road + house_number → line1
  address.postcode         → postal_code
  address.country_code     → country_code (uppercased)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import NotFoundError, ConflictError, ValidationError
from models.address import Address
from repositories.address_repository import AddressRepository
from schemas.address import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
    NominatimResult,
)

if TYPE_CHECKING:
    from events.publisher import EventPublisher

log = structlog.get_logger(__name__)

_NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
_NOMINATIM_HEADERS = {
    "User-Agent": getattr(settings, "NOMINATIM_USER_AGENT", "Riviwa-GRM/1.0 (support@riviwa.com)"),
    "Accept-Language": "en",
}


# ─────────────────────────────────────────────────────────────────────────────
# Nominatim helpers (module-level, no DB access)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_nominatim_address(raw: dict) -> dict:
    """
    Convert one Nominatim JSON result into the Address model fields dict.
    Works for both /search (jsonv2) and /reverse results.
    """
    addr = raw.get("address", {})

    # line1: road + optional house number
    road  = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or ""
    house = addr.get("house_number") or ""
    line1 = f"{house} {road}".strip() or None

    # city: prefer city → town → village → municipality → suburb
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("suburb")
        or None
    )

    # region: OSM state
    region = addr.get("state") or None

    # district: prefer state_district, fall back to county
    district = addr.get("state_district") or addr.get("county") or None

    # lga: county (in Tanzania this often IS the LGA name)
    lga = addr.get("county") or None

    # ward: suburb or city_district
    ward = addr.get("suburb") or addr.get("city_district") or None

    # mtaa: quarter or neighbourhood
    mtaa = addr.get("quarter") or addr.get("neighbourhood") or None

    country_code = (addr.get("country_code") or "TZ").upper()
    postal_code  = addr.get("postcode") or None

    lat = raw.get("lat")
    lon = raw.get("lon")

    return {
        "line1":         line1,
        "city":          city,
        "postal_code":   postal_code,
        "country_code":  country_code,
        "region":        region,
        "district":      district,
        "lga":           lga,
        "ward":          ward,
        "mtaa":          mtaa,
        "gps_latitude":  float(lat) if lat else None,
        "gps_longitude": float(lon) if lon else None,
        "display_name":  raw.get("display_name"),
        "osm_id":        int(raw["osm_id"]) if raw.get("osm_id") else None,
        "osm_type":      raw.get("osm_type"),
        "place_id":      int(raw["place_id"]) if raw.get("place_id") else None,
        "place_rank":    int(raw["place_rank"]) if raw.get("place_rank") else None,
        "place_type":    raw.get("type"),
        "address_class": raw.get("class"),
    }


def _nominatim_to_result(raw: dict) -> NominatimResult:
    parsed = _parse_nominatim_address(raw)
    return NominatimResult(
        place_id      = int(raw["place_id"]),
        osm_id        = parsed["osm_id"],
        osm_type      = parsed["osm_type"],
        display_name  = parsed["display_name"] or "",
        place_rank    = parsed["place_rank"],
        place_type    = parsed["place_type"],
        address_class = parsed["address_class"],
        line1         = parsed["line1"],
        city          = parsed["city"],
        postal_code   = parsed["postal_code"],
        country_code  = parsed["country_code"],
        region        = parsed["region"],
        district      = parsed["district"],
        lga           = parsed["lga"],
        ward          = parsed["ward"],
        mtaa          = parsed["mtaa"],
        gps_latitude  = parsed["gps_latitude"],
        gps_longitude = parsed["gps_longitude"],
    )


async def _nominatim_get(path: str, params: dict) -> dict | list:
    """Low-level async Nominatim request."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_NOMINATIM_BASE}{path}",
            params={**params, "format": "jsonv2", "addressdetails": 1},
            headers=_NOMINATIM_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()


async def nominatim_search(
    query: str,
    *,
    countrycodes: Optional[str] = None,
    limit: int = 8,
) -> List[NominatimResult]:
    """
    Search Nominatim for addresses matching `query`.
    Returns up to `limit` NominatimResult objects.
    """
    params: dict = {"q": query, "limit": limit}
    if countrycodes:
        params["countrycodes"] = countrycodes
    try:
        results = await _nominatim_get("/search", params)
        if not isinstance(results, list):
            return []
        return [_nominatim_to_result(r) for r in results if r.get("place_id")]
    except httpx.HTTPError as exc:
        log.warning("nominatim_search_failed", query=query, error=str(exc))
        return []


async def nominatim_reverse(
    lat: float,
    lon: float,
) -> Optional[NominatimResult]:
    """
    Reverse-geocode a GPS coordinate via Nominatim /reverse.
    Returns None if Nominatim returns no result.
    """
    try:
        raw = await _nominatim_get("/reverse", {"lat": lat, "lon": lon})
        if not isinstance(raw, dict) or "place_id" not in raw:
            return None
        return _nominatim_to_result(raw)
    except httpx.HTTPError as exc:
        log.warning("nominatim_reverse_failed", lat=lat, lon=lon, error=str(exc))
        return None


def _empty_parsed(req: "AddressCreateRequest", place_id: int) -> dict:
    """Fallback parsed dict when Nominatim is unreachable — use client fields."""
    return {
        "line1": req.line1, "city": req.city,
        "postal_code": req.postal_code, "country_code": req.country_code or "TZ",
        "region": req.region, "district": req.district,
        "lga": req.lga, "ward": req.ward, "mtaa": req.mtaa,
        "display_name": None, "osm_id": None, "osm_type": None,
        "place_id": place_id, "place_rank": None,
        "place_type": None, "address_class": None,
        "gps_latitude": None, "gps_longitude": None,
    }


async def nominatim_lookup(place_id: int) -> Optional[dict]:
    """
    Fetch full details for a specific Nominatim place_id via /lookup.
    Uses osm_type + osm_id if place_id lookup requires it.
    Falls back to /details endpoint.
    """
    try:
        raw = await _nominatim_get("/details", {"place_id": place_id})
        if isinstance(raw, dict):
            return raw
    except httpx.HTTPError:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# AddressService
# ─────────────────────────────────────────────────────────────────────────────

class AddressService:

    def __init__(self, db: AsyncSession, publisher: "Optional[EventPublisher]" = None) -> None:
        self.db        = db
        self.repo      = AddressRepository(db)
        self.publisher = publisher

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, address_id: uuid.UUID) -> Address:
        address = await self.repo.get_by_id(address_id)
        if not address:
            raise NotFoundError(f"Address {address_id} not found.")
        return address

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> List[Address]:
        return await self.repo.list_by_entity(entity_type, entity_id)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, req: AddressCreateRequest) -> Address:
        """
        Create an address. GPS coordinates are always the precise ground truth.

        Modes (evaluated in order):
          · osm_place_id + GPS  → fetch OSM address text from Nominatim, store
                                   user-provided GPS as the exact location.
          · osm_place_id only   → fetch everything (text + coords) from Nominatim.
          · GPS only            → reverse-geocode via Nominatim for text fields,
                                   store user-provided GPS as exact coordinates.
          · neither             → manual: store exactly what the user sent.

        GPS supplied by the user is NEVER replaced by Nominatim coordinates.
        """
        has_osm = req.osm_place_id is not None
        has_gps = req.gps_latitude is not None and req.gps_longitude is not None

        if has_osm:
            # OSM lookup for address text; GPS (if any) pinned as exact location
            address = await self._create_from_osm(req)
        elif has_gps:
            # Reverse-geocode GPS for address text; GPS is exact location
            address = await self._create_from_gps(req)
        else:
            address = self._create_manual(req)

        # If is_default, clear other defaults first
        if address.is_default:
            await self.repo.clear_defaults(
                req.entity_type,
                req.entity_id,
                exclude_id=None,
            )
        elif await self.repo.count_by_entity(req.entity_type, req.entity_id) == 0:
            # First address for this entity → auto-set as default
            address.is_default = True

        address = await self.repo.create(address)
        if self.publisher:
            await self.publisher.address_created(address)
        return address

    async def _create_from_osm(self, req: AddressCreateRequest) -> Address:
        """
        Build an address from an OSM place selection.

        The frontend receives a full NominatimResult from GET /addresses/search
        (which includes all text fields). When it POSTs with osm_place_id it
        should also echo those text fields (line1, ward, region, display_name,
        etc.) back in the request body — they are used directly, with no
        second Nominatim round-trip needed.

        If the client sends only osm_place_id with no text fields (bare mode),
        we fall back to a Nominatim reverse lookup using the GPS pin (if any)
        or a Nominatim /search by place_id.

        GPS rule: user-supplied lat/lon is always the exact stored location.
        Nominatim's own coordinates are never used in their place.
        """
        # Determine whether the client already provided address text fields
        # (the normal flow: user picked from search results → fields populated)
        client_has_text = any([
            req.line1, req.city, req.region, req.district,
            req.lga, req.ward, req.mtaa, req.display_name,
        ])

        if client_has_text:
            # Use the fields the client echoed from the NominatimResult
            parsed = {
                "line1":         req.line1,
                "city":          req.city,
                "postal_code":   req.postal_code,
                "country_code":  req.country_code or "TZ",
                "region":        req.region,
                "district":      req.district,
                "lga":           req.lga,
                "ward":          req.ward,
                "mtaa":          req.mtaa,
                "display_name":  req.display_name,
                # OSM metadata echoed from NominatimResult
                "osm_id":        req.osm_id,
                "osm_type":      req.osm_type,
                "place_id":      req.osm_place_id,
                "place_rank":    None,
                "place_type":    None,
                "address_class": None,
                # Nominatim coords irrelevant — overridden below
                "gps_latitude":  None,
                "gps_longitude": None,
            }
        else:
            # Bare osm_place_id — try GPS reverse first, then Nominatim lookup
            if req.gps_latitude is not None:
                result = await nominatim_reverse(req.gps_latitude, req.gps_longitude)
                if result:
                    parsed = {
                        "line1": result.line1, "city": result.city,
                        "postal_code": result.postal_code,
                        "country_code": result.country_code or "TZ",
                        "region": result.region, "district": result.district,
                        "lga": result.lga, "ward": result.ward, "mtaa": result.mtaa,
                        "display_name": result.display_name,
                        "osm_id": result.osm_id, "osm_type": result.osm_type,
                        "place_id": req.osm_place_id,
                        "place_rank": result.place_rank,
                        "place_type": result.place_type,
                        "address_class": result.address_class,
                        "gps_latitude": None, "gps_longitude": None,
                    }
                else:
                    parsed = _empty_parsed(req, req.osm_place_id)
            else:
                raw = await nominatim_lookup(req.osm_place_id)
                parsed = _parse_nominatim_address(raw) if raw else _empty_parsed(req, req.osm_place_id)

        # GPS supplied by user is ground truth — never let Nominatim override it.
        stored_lat = req.gps_latitude  if req.gps_latitude  is not None else parsed["gps_latitude"]
        stored_lon = req.gps_longitude if req.gps_longitude is not None else parsed["gps_longitude"]

        return Address(
            entity_type   = req.entity_type,
            entity_id     = req.entity_id,
            user_id       = req.entity_id if req.entity_type == "user" else None,
            subproject_id = req.entity_id if req.entity_type == "org_subproject" else None,
            address_type  = req.address_type,
            label         = req.label,
            is_default    = req.is_default,
            source        = "osm",
            place_id      = parsed["place_id"] or req.osm_place_id,
            osm_id        = parsed["osm_id"],
            osm_type      = parsed["osm_type"],
            display_name  = parsed["display_name"],
            place_rank    = parsed["place_rank"],
            place_type    = parsed["place_type"],
            address_class = parsed["address_class"],
            line1         = parsed["line1"],
            line2         = req.line2,
            city          = parsed["city"],
            state         = req.state,
            postal_code   = parsed["postal_code"],
            country_code  = parsed["country_code"],
            region        = parsed["region"],
            district      = parsed["district"],
            lga           = parsed["lga"],
            ward          = parsed["ward"],
            mtaa          = parsed["mtaa"],
            gps_latitude  = stored_lat,
            gps_longitude = stored_lon,
            address_notes = req.address_notes,
        )

    async def _create_from_gps(self, req: AddressCreateRequest) -> Address:
        """
        Reverse-geocode the user's GPS coordinates via Nominatim to populate
        address text fields.

        GPS rule: req.gps_latitude / req.gps_longitude are always stored
        unchanged.  Nominatim's own lat/lon from the reverse result is discarded —
        the user-supplied pin is more precise than any OSM centroid.
        """
        result = await nominatim_reverse(req.gps_latitude, req.gps_longitude)

        if result:
            return Address(
                entity_type   = req.entity_type,
                entity_id     = req.entity_id,
                user_id       = req.entity_id if req.entity_type == "user" else None,
                subproject_id = req.entity_id if req.entity_type == "org_subproject" else None,
                address_type  = req.address_type,
                label         = req.label,
                is_default    = req.is_default,
                source        = "gps",
                place_id      = result.place_id,
                osm_id        = result.osm_id,
                osm_type      = result.osm_type,
                display_name  = result.display_name,
                place_rank    = result.place_rank,
                place_type    = result.place_type,
                address_class = result.address_class,
                line1         = result.line1 or req.line1,
                line2         = req.line2,
                city          = result.city or req.city,
                state         = req.state,
                postal_code   = result.postal_code or req.postal_code,
                country_code  = result.country_code or req.country_code,
                region        = result.region or req.region,
                district      = result.district or req.district,
                lga           = result.lga or req.lga,
                ward          = result.ward or req.ward,
                mtaa          = result.mtaa or req.mtaa,
                # Always the user's exact pin — never result.gps_latitude/lon
                gps_latitude  = req.gps_latitude,
                gps_longitude = req.gps_longitude,
                address_notes = req.address_notes,
            )
        else:
            # Nominatim returned nothing → store GPS + manual fields
            log.info(
                "nominatim_reverse_no_result",
                lat=req.gps_latitude,
                lon=req.gps_longitude,
            )
            return Address(
                entity_type   = req.entity_type,
                entity_id     = req.entity_id,
                user_id       = req.entity_id if req.entity_type == "user" else None,
                subproject_id = req.entity_id if req.entity_type == "org_subproject" else None,
                address_type  = req.address_type,
                label         = req.label,
                is_default    = req.is_default,
                source        = "gps",
                line1         = req.line1,
                line2         = req.line2,
                city          = req.city,
                state         = req.state,
                postal_code   = req.postal_code,
                country_code  = req.country_code,
                region        = req.region,
                district      = req.district,
                lga           = req.lga,
                ward          = req.ward,
                mtaa          = req.mtaa,
                gps_latitude  = req.gps_latitude,
                gps_longitude = req.gps_longitude,
                address_notes = req.address_notes,
            )

    def _create_manual(self, req: AddressCreateRequest) -> Address:
        """Build an Address object from manually entered fields."""
        return Address(
            entity_type   = req.entity_type,
            entity_id     = req.entity_id,
            user_id       = req.entity_id if req.entity_type == "user" else None,
            subproject_id = req.entity_id if req.entity_type == "org_subproject" else None,
            address_type  = req.address_type,
            label         = req.label,
            is_default    = req.is_default,
            source        = "manual",
            line1         = req.line1,
            line2         = req.line2,
            city          = req.city,
            state         = req.state,
            postal_code   = req.postal_code,
            country_code  = req.country_code,
            region        = req.region,
            district      = req.district,
            lga           = req.lga,
            ward          = req.ward,
            mtaa          = req.mtaa,
            gps_latitude  = req.gps_latitude,
            gps_longitude = req.gps_longitude,
            address_notes = req.address_notes,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        address_id: uuid.UUID,
        req: AddressUpdateRequest,
    ) -> Address:
        address = await self.get_by_id(address_id)

        fields = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}

        if fields.get("is_default") is True:
            await self.repo.clear_defaults(
                address.entity_type,
                address.entity_id,
                exclude_id=address_id,
            )

        updated = await self.repo.update_fields(address_id, fields)
        if self.publisher:
            await self.publisher.address_updated(updated, list(fields.keys()))
        return updated

    # ── Set default ───────────────────────────────────────────────────────────

    async def set_default(self, address_id: uuid.UUID) -> Address:
        address = await self.get_by_id(address_id)
        await self.repo.clear_defaults(
            address.entity_type,
            address.entity_id,
            exclude_id=address_id,
        )
        updated = await self.repo.update_fields(address_id, {"is_default": True})
        if self.publisher:
            await self.publisher.address_updated(updated, ["is_default"])
        return updated

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(self, address_id: uuid.UUID) -> None:
        address = await self.get_by_id(address_id)
        entity_type = address.entity_type
        entity_id   = address.entity_id
        await self.repo.delete(address)
        if self.publisher:
            await self.publisher.address_deleted(address_id, entity_type, entity_id)

    # ── Serialise ─────────────────────────────────────────────────────────────

    @staticmethod
    def to_response(address: Address) -> AddressResponse:
        return AddressResponse(
            id            = address.id,
            entity_type   = address.entity_type,
            entity_id     = address.entity_id,
            address_type  = address.address_type,
            label         = address.label,
            is_default    = address.is_default,
            source        = address.source,
            osm_id        = address.osm_id,
            osm_type      = address.osm_type,
            place_id      = address.place_id,
            display_name  = address.display_name,
            place_rank    = address.place_rank,
            place_type    = address.place_type,
            address_class = address.address_class,
            line1         = address.line1,
            line2         = address.line2,
            city          = address.city,
            state         = address.state,
            postal_code   = address.postal_code,
            country_code  = address.country_code,
            region        = address.region,
            district      = address.district,
            lga           = address.lga,
            ward          = address.ward,
            mtaa          = address.mtaa,
            gps_latitude  = address.gps_latitude,
            gps_longitude = address.gps_longitude,
            address_notes = address.address_notes,
            display_lines = address.full_address_lines(),
            created_at    = address.created_at,
            updated_at    = address.updated_at,
        )
