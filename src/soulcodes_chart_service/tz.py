"""IANA time zones loaded from the pinned `tzdata` package, never the host's zone files.

This keeps historical offsets identical on every machine and lets meta.engines record
the exact time zone database version used.
"""

from __future__ import annotations

import importlib.resources
from functools import lru_cache
from zoneinfo import ZoneInfo


@lru_cache(maxsize=1)
def _zones_by_lower_name() -> dict[str, str]:
    names = importlib.resources.files("tzdata").joinpath("zones").read_text().split()
    return {name.lower(): name for name in names}


def canonical_zone_name(name: str) -> str | None:
    """The correctly cased IANA name ("australia/sydney" -> "Australia/Sydney"), or None."""
    return _zones_by_lower_name().get(name.strip().lower())


@lru_cache(maxsize=256)
def load_zone(name: str) -> ZoneInfo:
    """Load a zone by IANA name; raises KeyError for unknown names."""
    canonical = canonical_zone_name(name)
    if canonical is None:
        raise KeyError(name)
    resource = importlib.resources.files("tzdata.zoneinfo").joinpath(*canonical.split("/"))
    with resource.open("rb") as handle:
        return ZoneInfo.from_file(handle, key=canonical)
