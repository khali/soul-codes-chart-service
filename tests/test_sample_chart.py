"""Regression check on a fictional person: "Sample Person", 1985-07-04 15:00, Melbourne.

Every expected value below was produced by this service's own engines and then reviewed for
internal consistency (the defined centres, channels and gates agree with the type and
authority). Unlike a cross-check against an independent reference chart, this guards against
unintended changes in the calculation; it does not prove the calculation correct by itself.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from soulcodes_chart_service.hd.calculator import calculate

EXPECTED_PERSONALITY = [
    ("sun", 39, 3), ("earth", 38, 3), ("moon", 41, 3), ("north_node", 2, 4),
    ("south_node", 1, 4), ("mercury", 31, 5), ("venus", 8, 4), ("mars", 53, 2),
    ("jupiter", 13, 3), ("saturn", 43, 4), ("uranus", 5, 4), ("neptune", 10, 4), ("pluto", 50, 6),
]  # fmt: skip
EXPECTED_DESIGN = [
    ("sun", 21, 5), ("earth", 48, 5), ("moon", 6, 1), ("north_node", 2, 6),
    ("south_node", 1, 6), ("mercury", 21, 5), ("venus", 21, 5), ("mars", 2, 2),
    ("jupiter", 19, 5), ("saturn", 14, 4), ("uranus", 26, 1), ("neptune", 10, 6), ("pluto", 28, 3),
]  # fmt: skip


def test_human_design_headlines(sample: dict) -> None:
    hd = sample["humanDesign"]
    assert hd["type"] == "Manifesting Generator"
    assert hd["profile"] == "3/5"
    assert hd["authority"] == "Sacral"
    assert hd["definition"] == "Split Definition"
    assert hd["incarnationCross"] == "Right Angle Cross of Tension 2 (39/38 | 21/48)"
    assert hd["strategy"] == "To respond, then inform"
    assert hd["signature"] == "Satisfaction"
    assert hd["notSelfTheme"] == "Frustration"


def test_defined_centres_and_channels(sample: dict) -> None:
    hd = sample["humanDesign"]
    assert hd["definedCenters"] == ["throat", "g", "sacral", "spleen", "root"]
    assert hd["channels"] == [
        {"gates": [1, 8], "name": "Inspiration", "centers": ["g", "throat"]},
        {"gates": [2, 14], "name": "The Beat", "centers": ["g", "sacral"]},
        {"gates": [28, 38], "name": "Struggle", "centers": ["spleen", "root"]},
    ]


@pytest.mark.parametrize(
    ("side", "expected"), [("personality", EXPECTED_PERSONALITY), ("design", EXPECTED_DESIGN)]
)
def test_all_activations(sample: dict, side: str, expected: list) -> None:
    activations = sample["humanDesign"]["activations"][side]
    got = [(a["planet"], a["gate"], a["line"]) for a in activations]
    assert sorted(got) == sorted(expected)
    assert [a["planet"] for a in activations][:5] == ["sun", "earth", "moon", "north_node", "south_node"]


def test_design_moment() -> None:
    birth = datetime(1985, 7, 4, 15, 0, tzinfo=ZoneInfo("Australia/Melbourne"))
    design = calculate(birth).design_moment
    # The design moment is the instant the Sun was 88 degrees of arc earlier: 1985-04-03 23:56 UTC.
    assert abs((design - datetime(1985, 4, 3, 23, 56, 46, tzinfo=UTC)).total_seconds()) < 60


def test_birth_moment_in_utc(sample: dict) -> None:
    # Melbourne is on standard time (UTC+10) in July.
    assert sample["birth"]["utcDateTime"] == "1985-07-04T05:00:00Z"
    assert sample["birth"]["timezone"] == "Australia/Melbourne"
    assert sample["birth"]["timeKnown"] is True


def test_sun_in_early_cancer(sample: dict) -> None:
    sun = sample["astrology"]["bigThree"]["sun"]
    assert sun["sign"] == "cancer"
    assert sun["degree"] == pytest.approx(12.17, abs=0.01)


def test_astrology_headlines(sample: dict) -> None:
    astro = sample["astrology"]
    assert astro["houseSystem"] == "placidus"
    assert astro["bigThree"]["moon"]["sign"] == "aquarius"
    assert astro["bigThree"]["ascendant"]["sign"] == "sagittarius"
    assert astro["angles"]["midheaven"] == pytest.approx(139.70, abs=0.01)  # 19 Leo
    assert len(astro["houses"]) == 12
    assert {p["key"] for p in astro["planets"]} >= {"sun", "moon", "north_node", "south_node", "chiron"}


def test_no_warnings_for_a_clear_chart(sample: dict) -> None:
    assert sample["meta"]["warnings"] == []


def test_astrology_and_human_design_agree_on_the_sun(sample: dict) -> None:
    """Kerykeion and the Human Design engine must place the Sun identically."""
    sun = sample["astrology"]["bigThree"]["sun"]["longitude"]
    birth = datetime(1985, 7, 4, 5, 0, tzinfo=UTC)
    hd_sun = next(a for a in calculate(birth).personality if a.planet == "sun")
    assert hd_sun.longitude == pytest.approx(sun, abs=0.0001)
