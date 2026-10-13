"""Astrology: placements, houses (including polar fallback), aspects and unknown times."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from kerykeion import AstrologicalSubjectFactory

from soulcodes_chart_service.astro import calculator as astro
from soulcodes_chart_service.astro.aspects import aspect_between, find_aspects, orb_allowance
from soulcodes_chart_service.astro.houses import (
    POLAR_WARNING,
    calculate_houses,
    house_of,
)
from soulcodes_chart_service.astro.uncertainty import sign_change_warnings
from soulcodes_chart_service.astro.zodiac import placement, separation

SAMPLE_UTC = datetime(1985, 7, 4, 5, 0, tzinfo=UTC)
SYDNEY = (-33.86785, 151.20732)


class TestPlacement:
    def test_sign_and_degree(self) -> None:
        assert placement(340.5) == {"sign": "pisces", "degree": 10.5, "longitude": 340.5}
        assert placement(0.0)["sign"] == "aries"
        assert placement(30.0) == {"sign": "taurus", "degree": 0.0, "longitude": 30.0}

    def test_rounding_never_reaches_thirty_or_360(self) -> None:
        assert placement(29.999999) == {"sign": "taurus", "degree": 0.0, "longitude": 30.0}
        assert placement(359.999999) == {"sign": "aries", "degree": 0.0, "longitude": 0.0}
        assert placement(-10.0)["sign"] == "pisces"

    def test_separation_wraps(self) -> None:
        assert separation(350, 10) == 20
        assert separation(10, 190) == 180


class TestHouses:
    def test_matches_kerykeion_below_polar_limit(self) -> None:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name="check", year=1985, month=7, day=4, hour=5, minute=0,
            lng=SYDNEY[1], lat=SYDNEY[0], tz_str="UTC", online=False, suppress_geonames_warning=True,
        )  # fmt: skip
        houses = calculate_houses(astro.julian_day_ut(SAMPLE_UTC), *SYDNEY)
        assert houses.system == "placidus" and houses.warning is None
        assert houses.ascendant == pytest.approx(subject.ascendant.abs_pos, abs=1e-6)
        assert houses.midheaven == pytest.approx(subject.medium_coeli.abs_pos, abs=1e-6)
        assert houses.cusps[1] == pytest.approx(subject.second_house.abs_pos, abs=1e-6)

    def test_polar_birth_uses_whole_sign_at_true_latitude(self) -> None:
        """Tromsø, 69.65 N. Kerykeion would clamp to 66 N and move the Ascendant."""
        moment = datetime(1990, 6, 21, 10, 0, tzinfo=UTC)
        houses = calculate_houses(astro.julian_day_ut(moment), 69.6489, 18.95508)
        clamped = calculate_houses(astro.julian_day_ut(moment), 66.0, 18.95508)
        assert houses.system == "whole_sign"
        assert houses.warning == POLAR_WARNING
        assert houses.ascendant != pytest.approx(clamped.ascendant, abs=0.1)
        sign_start = houses.ascendant - houses.ascendant % 30
        assert houses.cusps[0] == pytest.approx(sign_start)
        assert all(
            (b - a) % 360 == pytest.approx(30) for a, b in zip(houses.cusps, houses.cusps[1:], strict=False)
        )

    def test_house_of_handles_wrap_around(self) -> None:
        cusps = (350.0, 20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 320.0)
        assert house_of(355.0, cusps) == 1
        assert house_of(5.0, cusps) == 1
        assert house_of(20.0, cusps) == 2
        assert house_of(349.9, cusps) == 12


class TestAspects:
    def test_orbs_take_the_smaller_allowance(self) -> None:
        assert orb_allowance("sun", "moon", "conjunction") == 10
        assert orb_allowance("sun", "mars", "conjunction") == 8
        assert orb_allowance("sun", "north_node", "conjunction") == 5
        assert orb_allowance("ascendant", "venus", "sextile") == 4

    def test_aspect_detection_and_orb(self) -> None:
        assert aspect_between("sun", 10.0, "moon", 129.0) == {
            "a": "sun",
            "b": "moon",
            "type": "trine",
            "orb": 1.0,
        }
        assert aspect_between("sun", 10.0, "mars", 196.0) == {
            "a": "sun",
            "b": "mars",
            "type": "opposition",
            "orb": 6.0,
        }
        assert aspect_between("sun", 10.0, "mars", 200.0) is None  # 10 degrees: beyond the planet orb of 8
        assert aspect_between("mars", 0.0, "venus", 9.0) is None  # beyond 8 degrees
        assert aspect_between("north_node", 0.0, "chiron", 5.0) is not None
        assert aspect_between("north_node", 0.0, "chiron", 5.01) is None

    def test_trivial_pairs_skipped(self) -> None:
        assert aspect_between("north_node", 0.0, "south_node", 180.0) is None
        assert aspect_between("ascendant", 0.0, "midheaven", 90.0) is None

    def test_sorted_tightest_first(self) -> None:
        aspects = find_aspects({"sun": 0.0, "moon": 95.0, "mars": 121.0})
        assert [a["orb"] for a in aspects] == sorted(a["orb"] for a in aspects)
        assert {(a["a"], a["b"], a["type"]) for a in aspects} == {
            ("sun", "moon", "square"),
            ("sun", "mars", "trine"),
        }


class TestCharts:
    def test_known_time_chart_shape(self) -> None:
        result = astro.calculate_known_time(SAMPLE_UTC, *SYDNEY)
        payload = result.payload
        assert [p["key"] for p in payload["planets"]] == list(astro.PLANET_ATTRIBUTES)
        assert all(1 <= p["house"] <= 12 for p in payload["planets"])
        nodes = {p["key"]: p for p in payload["planets"] if p["key"].endswith("node")}
        assert separation(
            nodes["north_node"]["longitude"], nodes["south_node"]["longitude"]
        ) == pytest.approx(180)
        assert {a["a"] for a in payload["aspects"]} | {a["b"] for a in payload["aspects"]} >= {"ascendant"}

    def test_unknown_time_chart_has_no_houses(self) -> None:
        payload = astro.calculate_unknown_time(SAMPLE_UTC, *SYDNEY).payload
        assert payload["houses"] is None and payload["angles"] is None
        assert payload["big_three"]["ascendant"] is None
        assert all(p["house"] is None for p in payload["planets"])
        bodies = {a["a"] for a in payload["aspects"]} | {a["b"] for a in payload["aspects"]}
        assert not bodies & {"ascendant", "midheaven"}

    def test_unknown_time_polar_records_whole_sign(self) -> None:
        payload = astro.calculate_unknown_time(SAMPLE_UTC, 70.0, 20.0).payload
        assert payload["house_system"] == "whole_sign"


class TestUnknownTimeWarnings:
    def _bodies(self, moon: float, sun: float = 10.0) -> list[astro.BodyPosition]:
        return [astro.BodyPosition("sun", sun, False), astro.BodyPosition("moon", moon, False)]

    def test_moon_staying_in_one_sign(self) -> None:
        warnings = sign_change_warnings(self._bodies(31.0), self._bodies(37.0), self._bodies(43.0))
        assert warnings == [
            "Birth time unknown: the Moon moves about 13 degrees a day, so its exact degree is "
            "uncertain. It stayed in Taurus all day."
        ]

    def test_bodies_changing_sign(self) -> None:
        warnings = sign_change_warnings(
            self._bodies(55.0, sun=29.8), self._bodies(61.0, sun=30.1), self._bodies(67.0, sun=30.6)
        )
        assert warnings == [
            "Birth time unknown: the Sun moved from Aries into Taurus that day, so either sign is "
            "possible. It is shown at midday, in Taurus.",
            "Birth time unknown: the Moon moved from Taurus into Gemini that day, so either sign is "
            "possible. It is shown at midday, in Gemini.",
        ]


class TestDateRangeEnds:
    """The first and last accepted dates must calculate at every UTC offset (-16 to +15 hours)."""

    def test_earliest_date_far_east(self) -> None:
        moment = datetime(1800, 12, 31, 9, 0, tzinfo=UTC)  # 1801-01-01 00:00 at UTC+15
        assert len(astro.planet_positions(moment, -33.9, 151.2)) == 13

    def test_latest_date_far_west(self) -> None:
        moment = datetime(2399, 12, 31, 15, 59, tzinfo=UTC)  # 2399-12-30 23:59 at UTC-16
        assert len(astro.planet_positions(moment, 0.0, -179.0)) == 13

    def test_missing_point_raises_clearly(self) -> None:
        with pytest.raises(RuntimeError, match="No position for chiron"):
            astro.planet_positions(datetime(1799, 12, 31, 12, 0, tzinfo=UTC), 0.0, 0.0)
