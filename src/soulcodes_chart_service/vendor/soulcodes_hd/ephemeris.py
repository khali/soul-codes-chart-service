# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/core/calculation_engine.py
#   ChartCalculationEngine._calculate_planetary_positions and
#   ChartCalculationEngine._find_design_date
# Changes:
#   - methods lifted to module-level functions; unused lat/lon parameters dropped
#     (geocentric longitudes do not depend on the observer)
#   - debug logging removed
#   - a failed planet calculation now raises instead of silently returning 0.0
#   - the design-date search raises if it does not converge instead of returning None
#   - inputs must be timezone-aware; they are converted to UTC first
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""Planetary longitudes and the Human Design 'design' moment (88 solar degrees before birth)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import swisseph as swe

# Planets used by Human Design. TRUE node, as upstream ("matches reference screenshots").
HD_PLANETS: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "North Node": swe.TRUE_NODE,
}

DESIGN_SOLAR_ARC = 88.0
_DESIGN_TOLERANCE = 0.00001


def _to_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return moment.astimezone(UTC)


def _julian_day(moment: datetime) -> float:
    hour = moment.hour + moment.minute / 60.0 + moment.second / 3600.0
    return swe.julday(moment.year, moment.month, moment.day, hour)


def _sun_longitude(moment: datetime) -> float:
    return swe.calc_ut(_julian_day(moment), swe.SUN, swe.FLG_MOSEPH)[0][0]


def calculate_planetary_positions(moment: datetime) -> dict[str, float]:
    """Ecliptic longitudes (Moshier ephemeris) for the HD planets plus Earth and South Node."""
    jd = _julian_day(_to_utc(moment))
    positions: dict[str, float] = {}
    for planet_name, planet_id in HD_PLANETS.items():
        result, _flags = swe.calc_ut(jd, planet_id, swe.FLG_MOSEPH)
        positions[planet_name] = result[0]

    positions["Earth"] = (positions["Sun"] + 180) % 360
    positions["South Node"] = (positions["North Node"] + 180) % 360
    return positions


def find_design_date(birth_moment: datetime) -> datetime:
    """Binary-search the UTC moment when the Sun was 88 degrees behind its birth position."""
    birth_utc = _to_utc(birth_moment)
    birth_sun = _sun_longitude(birth_utc)

    start_timestamp = int((birth_utc - timedelta(days=96)).timestamp())
    end_timestamp = int((birth_utc - timedelta(days=84)).timestamp())

    for _ in range(100):
        mid_timestamp = (start_timestamp + end_timestamp) // 2
        mid_date = datetime.fromtimestamp(mid_timestamp, tz=UTC)

        difference = abs(birth_sun - _sun_longitude(mid_date))
        if difference > 180:
            difference = 360 - difference

        if abs(difference - DESIGN_SOLAR_ARC) < _DESIGN_TOLERANCE:
            return mid_date
        if difference > DESIGN_SOLAR_ARC:
            start_timestamp = mid_timestamp
        else:
            end_timestamp = mid_timestamp

    raise RuntimeError("Design date search did not converge")
