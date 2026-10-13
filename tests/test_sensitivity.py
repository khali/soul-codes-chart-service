"""Warnings when a 15-minute change in birth time would change headline results."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from soulcodes_chart_service.astro.calculator import julian_day_ut
from soulcodes_chart_service.astro.houses import calculate_houses
from soulcodes_chart_service.astro.zodiac import sign_of
from soulcodes_chart_service.hd.calculator import calculate
from soulcodes_chart_service.sensitivity import ascendant_warning, human_design_warning, planet_sign_warnings

SYDNEY = (-33.86785, 151.20732)


def _ascendant_cusp_moment(start: datetime) -> datetime:
    """First minute after `start` at which the Ascendant changes sign in Sydney."""
    previous = sign_of(calculate_houses(julian_day_ut(start), *SYDNEY).ascendant)
    for minute in range(1, 240):
        moment = start + timedelta(minutes=minute)
        current = sign_of(calculate_houses(julian_day_ut(moment), *SYDNEY).ascendant)
        if current != previous:
            return moment
    raise AssertionError("no Ascendant sign change found")


def test_no_ascendant_warning_mid_sign() -> None:
    # The sample Ascendant is 12 degrees into Sagittarius: far from either edge.
    assert ascendant_warning(datetime(1985, 7, 4, 5, 0, tzinfo=UTC), *SYDNEY) is None


def test_ascendant_warning_near_cusp() -> None:
    cusp = _ascendant_cusp_moment(datetime(1985, 7, 4, 5, 0, tzinfo=UTC))
    warning = ascendant_warning(cusp + timedelta(minutes=2), *SYDNEY)
    assert warning is not None
    assert warning.startswith("The Ascendant is at the very edge of ")
    assert "15 minutes different would put it in " in warning


def test_no_human_design_warning_for_the_sample() -> None:
    birth = datetime(1985, 7, 4, 5, 0, tzinfo=UTC)
    assert human_design_warning(birth, calculate(birth)) is None


def test_human_design_warning_when_profile_is_on_a_line_edge() -> None:
    # Find a moment where the personality Sun changes line; 15 minutes is ~0.01 degrees,
    # so search minute by minute around a known line boundary of the Sun.
    start = datetime(1985, 7, 4, 5, 0, tzinfo=UTC)
    base_line = next(a.line for a in calculate(start).personality if a.planet == "sun")
    moment = start
    while next(a.line for a in calculate(moment).personality if a.planet == "sun") == base_line:
        moment += timedelta(hours=1)
    # Narrow to the minute.
    moment -= timedelta(hours=1)
    while next(a.line for a in calculate(moment).personality if a.planet == "sun") == base_line:
        moment += timedelta(minutes=1)
    warning = human_design_warning(moment, calculate(moment))
    assert warning is not None
    assert "profile" in warning
    assert warning.endswith("so these rest on the recorded time being accurate.")


def test_sun_at_the_edge_of_a_sign() -> None:
    # Spring equinox 2000: the Sun entered Aries at 07:35 UTC on 20 March.
    warnings = planet_sign_warnings(datetime(2000, 3, 20, 7, 30, tzinfo=UTC), 51.5, -0.13)
    assert warnings == [
        "The Sun is at the very edge of Pisces: a birth time 15 minutes different would put it in Aries."
    ]


def test_no_planet_warnings_for_the_sample() -> None:
    assert planet_sign_warnings(datetime(1985, 7, 4, 5, 0, tzinfo=UTC), *SYDNEY) == []
