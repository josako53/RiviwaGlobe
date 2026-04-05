"""services/geo_service.py — Geospatial calculations."""
from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

from core.config import settings


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def tiered_geo_score(
    distance_km: float,
    same_city: bool = False,
    same_region: bool = False,
    same_country: bool = False,
) -> float:
    """
    Tiered proximity score.
    Same city → 1.0, then distance-based tiers.
    """
    if same_city:
        return 1.0
    if distance_km <= settings.GEO_TIER_CITY:
        return 1.0
    if distance_km <= settings.GEO_TIER_DISTRICT:
        return 0.75
    if distance_km <= settings.GEO_TIER_REGION:
        return 0.50
    if distance_km <= settings.GEO_TIER_COUNTRY:
        return 0.25
    return 0.10


def compute_geo_score(
    lat1: float | None, lon1: float | None,
    lat2: float | None, lon2: float | None,
    city1: str | None = None, city2: str | None = None,
    region1: str | None = None, region2: str | None = None,
    country1: str | None = None, country2: str | None = None,
) -> tuple[float, float | None]:
    """
    Returns (score, distance_km).
    If coordinates are missing, falls back to admin boundary matching.
    """
    # Both have coordinates — use haversine
    if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
        dist = haversine_km(lat1, lon1, lat2, lon2)
        same_city = bool(city1 and city2 and city1.lower() == city2.lower())
        same_region = bool(region1 and region2 and region1.lower() == region2.lower())
        return tiered_geo_score(dist, same_city=same_city, same_region=same_region), dist

    # Fallback: admin boundary matching
    if city1 and city2 and city1.lower() == city2.lower():
        return 1.0, None
    if region1 and region2 and region1.lower() == region2.lower():
        return 0.50, None
    if country1 and country2 and country1.lower() == country2.lower():
        return 0.25, None
    return 0.10, None
