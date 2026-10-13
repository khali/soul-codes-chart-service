"""Tropical natal chart: planets, houses, angles and aspects, via Kerykeion and pyswisseph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import swisseph as swe
from kerykeion import AstrologicalSubjectFactory

from .aspects import find_aspects
from .houses import PLACIDUS_LATITUDE_LIMIT, calculate_houses, house_of
from .zodiac import placement

# Contract PlanetKey -> Kerykeion attribute, in display order.
PLANET_ATTRIBUTES: dict[str, str] = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter",
    "saturn": "saturn",
    "uranus": "uranus",
    "neptune": "neptune",
    "pluto": "pluto",
    "north_node": "true_north_lunar_node",
    "south_node": "true_south_lunar_node",
    "chiron": "chiron",
}

ACTIVE_POINTS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
    "Neptune", "Pluto", "True_North_Lunar_Node", "True_South_Lunar_Node", "Chiron",
]  # fmt: skip


@dataclass(frozen=True)
class BodyPosition:
    key: str
    longitude: float
    retrograde: bool


@dataclass
class AstrologyResult:
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def julian_day_ut(moment: datetime) -> float:
    utc = moment.astimezone(UTC)
    hours = utc.hour + utc.minute / 60 + utc.second / 3600
    return swe.julday(utc.year, utc.month, utc.day, hours)


def planet_positions(moment: datetime, lat: float, lng: float) -> list[BodyPosition]:
    """Geocentric tropical positions of the contract planets at a moment."""
    utc = moment.astimezone(UTC)
    subject = AstrologicalSubjectFactory.from_birth_data(
        name="chart",
        year=utc.year,
        month=utc.month,
        day=utc.day,
        hour=utc.hour,
        minute=utc.minute,
        seconds=utc.second,
        lng=lng,
        lat=lat,
        tz_str="UTC",
        online=False,
        suppress_geonames_warning=True,
        active_points=ACTIVE_POINTS,
        calculate_lunar_phase=False,
    )
    positions = []
    for key, attribute in PLANET_ATTRIBUTES.items():
        point = getattr(subject, attribute)
        if point is None:  # Kerykeion logs and returns None when the ephemeris cannot answer
            raise RuntimeError(f"No position for {key} at {utc.isoformat()}")
        positions.append(BodyPosition(key, point.abs_pos, bool(point.retrograde)))
    return positions


def _planet_payload(body: BodyPosition, cusps: tuple[float, ...] | None) -> dict[str, Any]:
    house = house_of(body.longitude, cusps) if cusps else None
    return {"key": body.key, **placement(body.longitude), "house": house, "retrograde": body.retrograde}


def _by_key(bodies: list[BodyPosition]) -> dict[str, float]:
    return {body.key: body.longitude for body in bodies}


def calculate_known_time(moment: datetime, lat: float, lng: float) -> AstrologyResult:
    """A full chart when the birth time is known."""
    bodies = planet_positions(moment, lat, lng)
    houses = calculate_houses(julian_day_ut(moment), lat, lng)
    longitudes = _by_key(bodies) | {"ascendant": houses.ascendant, "midheaven": houses.midheaven}
    payload = {
        "zodiac": "tropical",
        "house_system": houses.system,
        "big_three": {
            "sun": placement(longitudes["sun"]),
            "moon": placement(longitudes["moon"]),
            "ascendant": placement(houses.ascendant),
        },
        "planets": [_planet_payload(body, houses.cusps) for body in bodies],
        "houses": [
            {"number": i + 1, "sign": placement(c)["sign"], "longitude": placement(c)["longitude"]}
            for i, c in enumerate(houses.cusps)
        ],
        "angles": {
            "ascendant": placement(houses.ascendant)["longitude"],
            "midheaven": placement(houses.midheaven)["longitude"],
        },
        "aspects": find_aspects(longitudes),
    }
    return AstrologyResult(payload, [houses.warning] if houses.warning else [])


def calculate_unknown_time(midday: datetime, lat: float, lng: float) -> AstrologyResult:
    """Planets only, at local midday; no houses, angles or Ascendant."""
    bodies = planet_positions(midday, lat, lng)
    longitudes = _by_key(bodies)
    payload = {
        "zodiac": "tropical",
        # No houses are drawn; this records the system a timed chart here would use.
        "house_system": "whole_sign" if abs(lat) > PLACIDUS_LATITUDE_LIMIT else "placidus",
        "big_three": {
            "sun": placement(longitudes["sun"]),
            "moon": placement(longitudes["moon"]),
            "ascendant": None,
        },
        "planets": [_planet_payload(body, None) for body in bodies],
        "houses": None,
        "angles": None,
        "aspects": find_aspects(longitudes),
    }
    return AstrologyResult(payload)
