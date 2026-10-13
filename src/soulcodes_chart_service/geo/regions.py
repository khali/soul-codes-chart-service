"""Country and state/province names as they appear in typed birthplaces."""

from __future__ import annotations

from functools import lru_cache

import geonamescache

from .text import normalise_name

# Common ways of writing a country that GeoNames does not list as the name.
COUNTRY_ALIASES: dict[str, str] = {
    "uk": "GB",
    "u k": "GB",
    "great britain": "GB",
    "britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "usa": "US",
    "us": "US",
    "u s a": "US",
    "u s": "US",
    "united states of america": "US",
    "america": "US",
    "holland": "NL",
    "the netherlands": "NL",
    "czech republic": "CZ",
    "korea": "KR",
    "republic of korea": "KR",
    "cote divoire": "CI",
    "viet nam": "VN",
    "uae": "AE",
    "eire": "IE",
    "republic of ireland": "IE",
    "burma": "MM",
    "nz": "NZ",
    "aotearoa": "NZ",
    "russian federation": "RU",
}

# GeoNames admin1 codes for the regions people most often add to a birthplace.
# The UK home nations double as countries above; they also narrow within GB.
_ADMIN1: dict[str, dict[str, str]] = {
    "AU": {
        "australian capital territory": "01", "act": "01",
        "new south wales": "02", "nsw": "02",
        "northern territory": "03", "nt": "03",
        "queensland": "04", "qld": "04",
        "south australia": "05", "sa": "05",
        "tasmania": "06", "tas": "06",
        "victoria": "07", "vic": "07",
        "western australia": "08", "wa": "08",
    },
    "CA": {
        "alberta": "01", "ab": "01", "british columbia": "02", "bc": "02",
        "manitoba": "03", "mb": "03", "new brunswick": "04", "nb": "04",
        "newfoundland and labrador": "05", "newfoundland": "05", "nl": "05",
        "nova scotia": "07", "ns": "07", "ontario": "08", "on": "08",
        "prince edward island": "09", "pei": "09", "quebec": "10", "qc": "10",
        "saskatchewan": "11", "sk": "11", "yukon": "12", "yt": "12",
        "northwest territories": "13", "nunavut": "14",
    },
    "GB": {
        "england": "ENG", "scotland": "SCT", "wales": "WLS", "northern ireland": "NIR",
    },
}  # fmt: skip


@lru_cache(maxsize=1)
def _countries() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for iso, country in geonamescache.GeonamesCache().get_countries().items():
        for label in (country["name"], country["iso"], country["iso3"]):
            lookup[normalise_name(label)] = iso
    lookup.update(COUNTRY_ALIASES)
    return lookup


@lru_cache(maxsize=1)
def _admin1() -> dict[str, dict[str, str]]:
    tables = {cc: dict(names) for cc, names in _ADMIN1.items()}
    us = tables.setdefault("US", {})
    for code, state in geonamescache.GeonamesCache().get_us_states().items():
        us[normalise_name(state["name"])] = code
        us[normalise_name(code)] = code
    return tables


def country_code(text: str) -> str | None:
    """ISO 3166 alpha-2 code for a typed country name, or None."""
    return _countries().get(normalise_name(text))


def admin1_codes(text: str, country: str | None) -> set[tuple[str, str]]:
    """(country, admin1) pairs a typed region could mean, limited to `country` if given."""
    key = normalise_name(text)
    matches = set()
    for cc, names in _admin1().items():
        if (country is None or cc == country) and key in names:
            matches.add((cc, names[key]))
    return matches
