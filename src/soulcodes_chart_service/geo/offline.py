"""Offline geocoder over the GeoNames city lists bundled with geonamescache.

No network: the data ships inside the geonamescache wheel (CC BY 4.0, GeoNames).
Each city is indexed by its name and its Latin-script alternative names.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import geonamescache

from .regions import admin1_codes, country_code
from .text import is_latin, normalise_name

SUPPORTED_POPULATIONS = (500, 1000, 5000, 15000)
_POSTCODE = re.compile(r"\b\d[\d\s-]*\b")


@dataclass(frozen=True)
class City:
    name: str
    country: str
    admin1: str
    latitude: float
    longitude: float
    population: int
    timezone: str | None


@dataclass(frozen=True)
class GeoMatch:
    """A geocoded place. `ambiguous` means other countries have a place of that name."""

    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str | None
    ambiguous: bool


@dataclass(frozen=True)
class _Query:
    names: list[str]  # candidate city names to try, most specific first
    hints: list[str]  # region or country words after the city name
    country: str | None


def _dataset_path(min_population: int) -> Path:
    if min_population not in SUPPORTED_POPULATIONS:
        raise ValueError(f"min_population must be one of {SUPPORTED_POPULATIONS}")
    return Path(geonamescache.__file__).parent / "data" / f"cities{min_population}.json"


def _parse(place: str) -> _Query:
    """Split "Hornsby NSW 2077, Australia" into names to try, region hints and a country."""
    parts = [p.strip() for p in place.split(",") if p.strip()]
    if not parts:
        return _Query([], [], None)
    country = country_code(parts[-1]) if len(parts) > 1 else None
    tokens = _POSTCODE.sub(" ", parts[0]).split()
    names = [" ".join(tokens[:n]) for n in range(len(tokens), 0, -1)]
    trailing = tokens[-1:] if len(tokens) > 1 else []
    return _Query(names, trailing + parts[1:], country)


class OfflineGeocoder:
    """Look up a typed birthplace such as "Wellington, New Zealand"."""

    def __init__(self, min_population: int = 5000) -> None:
        self._path = _dataset_path(min_population)
        self._index: dict[str, list[City]] | None = None
        self._lock = threading.Lock()

    def warm(self) -> None:
        """Load the index now rather than on the first request."""
        self._get_index()

    def _get_index(self) -> dict[str, list[City]]:
        with self._lock:
            if self._index is None:
                self._index = _build_index(self._path)
            return self._index

    def geocode(self, place: str) -> GeoMatch | None:
        query = _parse(place)
        index = self._get_index()
        for name in query.names:
            candidates = index.get(normalise_name(name))
            if candidates:
                return _choose(candidates, query)
        return None


def _build_index(path: Path) -> dict[str, list[City]]:
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    index: dict[str, list[City]] = {}
    for record in raw.values():
        city = City(
            name=record["name"],
            country=record["countrycode"],
            admin1=str(record.get("admin1code") or ""),
            latitude=float(record["latitude"]),
            longitude=float(record["longitude"]),
            population=int(record.get("population") or 0),
            timezone=record.get("timezone") or None,
        )
        keys = {normalise_name(record["name"])}
        keys.update(n for n in map(normalise_name, record.get("alternatenames", [])) if is_latin(n))
        for key in keys:
            index.setdefault(key, []).append(city)
    return index


def _narrow(candidates: list[City], hints: list[str], country: str | None) -> list[City] | None:
    """Candidates in the first hinted region that has any; None if no hint matched."""
    for hint in hints:
        regions = admin1_codes(hint, country)
        narrowed = [c for c in candidates if (c.country, c.admin1) in regions]
        if narrowed:
            return narrowed
    return None


def _choose(candidates: list[City], query: _Query) -> GeoMatch | None:
    pool = candidates
    country = query.country
    if country:
        pool = [c for c in candidates if c.country == country]
    if country and not pool:
        # "Portland, ME" or "Indianapolis, IN": a state code that is also a country code.
        pool = _narrow(candidates, query.hints[-1:], None) or []
        country = pool[0].country if pool else None
    if not pool:
        return None
    narrowed = _narrow(pool, query.hints, country)
    if narrowed is not None:
        pool = narrowed
    best = max(pool, key=lambda c: c.population)
    other_countries = {c.country for c in candidates} - {best.country}
    guessed = country is None and narrowed is None
    return GeoMatch(
        name=best.name,
        country=best.country,
        latitude=best.latitude,
        longitude=best.longitude,
        timezone=best.timezone,
        ambiguous=guessed and bool(other_countries),
    )
