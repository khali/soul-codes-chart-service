"""Geocoding (bundled GeoNames data, no network) and location resolution."""

from __future__ import annotations

import pytest

from soulcodes_chart_service.errors import PlaceAmbiguous, PlaceNotFound, TimezoneNotFound
from soulcodes_chart_service.geo.offline import GeoMatch, OfflineGeocoder
from soulcodes_chart_service.geo.resolver import resolve_location
from soulcodes_chart_service.geo.text import normalise_name

from .conftest import SYDNEY, FakeGeocoder, FakeTimezones


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("São Paulo", "sao paulo"),
        ("Białystok", "bialystok"),
        ("Saint-Denis", "saint denis"),
        ("St. Louis", "st louis"),
        ("  Tromsø ", "tromso"),
    ],
)
def test_normalise_name(text: str, expected: str) -> None:
    assert normalise_name(text) == expected


@pytest.mark.parametrize(
    ("place", "country", "zone"),
    [
        ("Sydney, Australia", "AU", "Australia/Sydney"),
        ("Wellington, New Zealand", "NZ", "Pacific/Auckland"),
        ("Hornsby NSW 2077, Australia", "AU", "Australia/Sydney"),
        ("Yamba NSW 2464, Australia", "AU", "Australia/Sydney"),
        ("São Paulo, State of São Paulo, Brazil", "BR", "America/Sao_Paulo"),
        ("Bialystok, Poland", "PL", "Europe/Warsaw"),
        ("London, England", "GB", "Europe/London"),
        ("London, Ontario, Canada", "CA", "America/Toronto"),
        ("Paris, Texas", "US", "America/Chicago"),
        ("Portland, ME", "US", "America/New_York"),  # ME is also Montenegro
        ("Indianapolis, IN", "US", "America/Indiana/Indianapolis"),  # IN is also India
        ("Bombay", "IN", "Asia/Kolkata"),  # alternative name
        ("Perth, Scotland", "GB", "Europe/London"),
    ],
)
def test_offline_geocoder_finds_places(
    offline_geocoder: OfflineGeocoder, place: str, country: str, zone: str
) -> None:
    match = offline_geocoder.geocode(place)
    assert match is not None
    assert (match.country, match.timezone) == (country, zone)
    assert match.ambiguous is False


def test_bare_name_picks_most_populous_and_flags_ambiguity(offline_geocoder: OfflineGeocoder) -> None:
    match = offline_geocoder.geocode("Wellington")
    assert match is not None
    assert match.country == "NZ"
    assert match.ambiguous is True


@pytest.mark.parametrize("place", ["Wellington, Australia", "Atlantisville, Nowhere", "", ",,,"])
def test_unknown_places(offline_geocoder: OfflineGeocoder, place: str) -> None:
    assert offline_geocoder.geocode(place) is None


def test_unsupported_population_threshold() -> None:
    with pytest.raises(ValueError):
        OfflineGeocoder(min_population=1234)


class TestResolveLocation:
    def test_supplied_values_win_and_skip_lookups(self) -> None:
        geocoder, zones = FakeGeocoder({}), FakeTimezones()
        location = resolve_location("Anywhere", -33.0, 151.0, "Australia/Sydney", geocoder, zones)
        assert (location.latitude, location.longitude, location.timezone) == (
            -33.0,
            151.0,
            "Australia/Sydney",
        )
        assert geocoder.calls == [] and zones.calls == []

    def test_coordinates_without_zone_look_up_the_zone(self) -> None:
        zones = FakeTimezones("Pacific/Auckland")
        location = resolve_location("Somewhere", -41.3, 174.8, None, FakeGeocoder({}), zones)
        assert location.timezone == "Pacific/Auckland"
        assert zones.calls == [(-41.3, 174.8)]

    def test_geocoded_place_supplies_coordinates_and_zone(self) -> None:
        location = resolve_location(
            "Sydney, Australia", None, None, None, FakeGeocoder(), FakeTimezones(None)
        )
        assert (location.latitude, location.longitude) == (SYDNEY.latitude, SYDNEY.longitude)
        assert location.timezone == "Australia/Sydney"

    def test_supplied_zone_overrides_geocoded_zone(self) -> None:
        location = resolve_location("Sydney, Australia", None, None, "UTC", FakeGeocoder(), FakeTimezones())
        assert location.timezone == "UTC"

    def test_ambiguous_place_adds_warning(self) -> None:
        match = GeoMatch("Wellington", "NZ", -41.28, 174.77, "Pacific/Auckland", ambiguous=True)
        location = resolve_location(
            "Wellington", None, None, None, FakeGeocoder({"Wellington": match}), FakeTimezones()
        )
        assert location.warnings == [
            "More than one place is called Wellington. We used Wellington, New Zealand; if that "
            "is wrong, add the country to the birthplace or send coordinates."
        ]

    def test_ambiguous_place_can_be_refused_instead_of_guessed(self) -> None:
        match = GeoMatch("Wellington", "NZ", -41.28, 174.77, "Pacific/Auckland", ambiguous=True)
        with pytest.raises(PlaceAmbiguous) as err:
            resolve_location(
                "Wellington",
                None,
                None,
                None,
                FakeGeocoder({"Wellington": match}),
                FakeTimezones(),
                reject_ambiguous=True,
            )
        assert err.value.code == "place_ambiguous" and err.value.status == 422
        assert "Wellington, New Zealand" in err.value.message

    def test_refusing_ambiguity_leaves_clear_places_and_coordinates_alone(self) -> None:
        clear = resolve_location(
            "Sydney, Australia", None, None, None, FakeGeocoder(), FakeTimezones(), reject_ambiguous=True
        )
        assert clear.timezone == "Australia/Sydney"
        given = resolve_location(
            "Wellington",
            -41.3,
            174.8,
            "Pacific/Auckland",
            FakeGeocoder({}),
            FakeTimezones(),
            reject_ambiguous=True,
        )
        assert given.timezone == "Pacific/Auckland"

    def test_unknown_place(self) -> None:
        with pytest.raises(PlaceNotFound) as err:
            resolve_location("Atlantis", None, None, None, FakeGeocoder({}), FakeTimezones())
        assert err.value.code == "place_not_found" and err.value.status == 422

    def test_zone_not_found_at_sea(self) -> None:
        with pytest.raises(TimezoneNotFound):
            resolve_location("Mid ocean", 0.0, -30.0, None, FakeGeocoder({}), FakeTimezones(None))
