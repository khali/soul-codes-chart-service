"""Zodiac sign helpers shared by the astrology modules."""

from __future__ import annotations

from typing import Any

SIGNS: tuple[str, ...] = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)  # fmt: skip

SIGN_LABELS: dict[str, str] = {sign: sign.capitalize() for sign in SIGNS}

DECIMALS = 4


def normalise(longitude: float) -> float:
    """Round to DECIMALS and wrap into [0, 360)."""
    return round(longitude, DECIMALS) % 360.0


def sign_of(longitude: float) -> str:
    return SIGNS[int(normalise(longitude) // 30)]


def placement(longitude: float) -> dict[str, Any]:
    """A SignPlacement: sign, degree within the sign, and ecliptic longitude."""
    lon = normalise(longitude)
    index = int(lon // 30)
    degree = min(round(lon - index * 30, DECIMALS), 29.9999)
    return {"sign": SIGNS[index], "degree": degree, "longitude": lon}


def separation(a: float, b: float) -> float:
    """Smallest angle between two longitudes, 0 to 180 degrees."""
    diff = abs(a - b) % 360.0
    return 360.0 - diff if diff > 180.0 else diff
