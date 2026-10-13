"""Versions of everything a chart depends on, recorded in meta.engines and /healthz."""

from __future__ import annotations

from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

import swisseph as swe

from .vendor.soulcodes_hd import SOURCE_COMMIT

_PACKAGES = ("kerykeion", "pyswisseph", "geonamescache", "timezonefinder", "tzdata")


def _version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "unknown"


@lru_cache(maxsize=1)
def engine_versions() -> dict[str, str]:
    engines = {"soulcodes-chart-service": _version("soulcodes-chart-service")}
    engines |= {package: _version(package) for package in _PACKAGES}
    engines["swiss-ephemeris"] = swe.version
    engines["ephemeris-data"] = "Moshier (built in) for planets and nodes; seas_18.se1 for Chiron"
    engines["soulcodes-hd"] = f"{SOURCE_COMMIT} (vendored subset)"
    engines["zodiac"] = "tropical"
    engines["lunar-node"] = "true node"
    return engines
