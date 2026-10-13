"""House cusps and angles straight from the Swiss Ephemeris.

Kerykeion clamps the latitude to +/-66 degrees before calculating houses, for every
house system, which silently moves the Ascendant for anyone born further north or
south. So houses and angles are calculated here with pyswisseph at the true latitude.
"""

from __future__ import annotations

from dataclasses import dataclass

import swisseph as swe

PLACIDUS_LATITUDE_LIMIT = 66.0

POLAR_WARNING = (
    "The birthplace is beyond 66 degrees of latitude, where Placidus houses cannot be "
    "calculated reliably, so whole sign houses are used instead."
)
PLACIDUS_FAILED_WARNING = (
    "Placidus houses could not be calculated for this time and place, so whole sign houses are used instead."
)


@dataclass(frozen=True)
class Houses:
    system: str  # "placidus" | "whole_sign"
    cusps: tuple[float, ...]  # 12 longitudes, house 1 first
    ascendant: float
    midheaven: float
    warning: str | None


def _swe_houses(julian_day_ut: float, lat: float, lng: float, code: bytes) -> tuple:
    cusps, ascmc = swe.houses_ex(julian_day_ut, lat, lng, code)
    return tuple(cusps[:12]), ascmc[0], ascmc[1]


def calculate_houses(julian_day_ut: float, lat: float, lng: float) -> Houses:
    """Placidus houses, or whole sign beyond the Placidus latitude limit."""
    if abs(lat) <= PLACIDUS_LATITUDE_LIMIT:
        try:
            cusps, asc, mc = _swe_houses(julian_day_ut, lat, lng, b"P")
            return Houses("placidus", cusps, asc, mc, None)
        except swe.Error:
            warning = PLACIDUS_FAILED_WARNING
    else:
        warning = POLAR_WARNING
    cusps, asc, mc = _swe_houses(julian_day_ut, lat, lng, b"W")
    return Houses("whole_sign", cusps, asc, mc, warning)


def house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    """House number (1-12) containing a longitude, given cusps in house order."""
    for index in range(12):
        start = cusps[index]
        end = cusps[(index + 1) % 12]
        span = (end - start) % 360.0
        if (longitude - start) % 360.0 < span:
            return index + 1
    raise ValueError(f"Longitude {longitude} not inside any house")
