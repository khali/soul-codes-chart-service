"""Decide where and in which time zone someone was born.

Supplied latitude/longitude/timezone always win. Whatever is missing is filled in:
coordinates (and usually the zone) by geocoding `place`, and the zone from the
coordinates when it is still unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

import geonamescache
from timezonefinder import TimezoneFinder

from ..errors import PlaceAmbiguous, PlaceNotFound, TimezoneNotFound
from ..tz import canonical_zone_name
from .offline import GeoMatch


class Geocoder(Protocol):
    def geocode(self, place: str) -> GeoMatch | None: ...


class TimezoneLookup(Protocol):
    def timezone_at(self, latitude: float, longitude: float) -> str | None: ...


class OfflineTimezoneLookup:
    """Time zone from coordinates using timezonefinder's bundled boundary data."""

    def __init__(self) -> None:
        self._finder: TimezoneFinder | None = None

    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        if self._finder is None:
            self._finder = TimezoneFinder()
        return self._finder.timezone_at(lng=longitude, lat=latitude)


@dataclass
class Location:
    latitude: float
    longitude: float
    timezone: str
    warnings: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _country_names() -> dict[str, str]:
    countries = geonamescache.GeonamesCache().get_countries()
    return {iso: country["name"] for iso, country in countries.items()}


def ambiguity_warning(match: GeoMatch) -> str:
    country = _country_names().get(match.country, match.country)
    return (
        f"More than one place is called {match.name}. We used {match.name}, {country}; "
        "if that is wrong, add the country to the birthplace or send coordinates."
    )


def _zone_for(
    timezone: str | None, match: GeoMatch | None, lat: float, lng: float, lookup: TimezoneLookup
) -> str:
    if timezone:
        return timezone
    candidate = match.timezone if match and match.timezone else lookup.timezone_at(lat, lng)
    canonical = canonical_zone_name(candidate) if candidate else None
    if canonical is None:
        raise TimezoneNotFound()
    return canonical


def resolve_location(
    place: str,
    latitude: float | None,
    longitude: float | None,
    timezone: str | None,
    geocoder: Geocoder,
    timezone_lookup: TimezoneLookup,
    reject_ambiguous: bool = False,
) -> Location:
    """Coordinates and IANA zone for a birth, geocoding only what was not supplied.

    A bare name that other countries share is normally answered with the most populous
    match and a warning. With `reject_ambiguous`, it is refused instead (`PlaceAmbiguous`),
    for callers with nobody to check the guess, such as a self-serve form.
    """
    match: GeoMatch | None = None
    warnings: list[str] = []
    if latitude is None or longitude is None:
        match = geocoder.geocode(place)
        if match is None:
            raise PlaceNotFound(place)
        latitude, longitude = match.latitude, match.longitude
        if match.ambiguous:
            if reject_ambiguous:
                raise PlaceAmbiguous(match.name, _country_names().get(match.country, match.country))
            warnings.append(ambiguity_warning(match))
    zone = _zone_for(timezone, match, latitude, longitude, timezone_lookup)
    return Location(latitude, longitude, zone, warnings)
