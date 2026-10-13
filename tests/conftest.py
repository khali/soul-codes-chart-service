"""Shared fixtures. All tests run offline: outbound sockets are blocked."""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from soulcodes_chart_service.app import create_app
from soulcodes_chart_service.config import Settings
from soulcodes_chart_service.geo.offline import GeoMatch, OfflineGeocoder

TOKEN = "test-token-" + "0123456789abcdef" * 2
AUTH = {"Authorization": f"Bearer {TOKEN}"}

SAMPLE_REQUEST = {
    "name": "Sample Person",
    "date": "1985-07-04",
    "time": "15:00",
    "place": "Melbourne, Australia",
    "latitude": None,
    "longitude": None,
    "timezone": None,
}

AMARA_REQUEST = {
    "name": "Amara",
    "date": "1988-03-14",
    "time": None,
    "place": "Wellington, New Zealand",
    "latitude": None,
    "longitude": None,
    "timezone": None,
}

SYDNEY = GeoMatch("Sydney", "AU", -33.86785, 151.20732, "Australia/Sydney", ambiguous=False)
MELBOURNE = GeoMatch("Melbourne", "AU", -37.814, 144.96332, "Australia/Melbourne", ambiguous=False)
WELLINGTON = GeoMatch("Wellington", "NZ", -41.28664, 174.77557, "Pacific/Auckland", ambiguous=False)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if anything tries to open a network connection."""

    def guard(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network access is not allowed in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


class FakeGeocoder:
    """Returns canned matches and records what it was asked."""

    def __init__(self, places: dict[str, GeoMatch] | None = None) -> None:
        self.places = (
            places if places is not None else {"Sydney, Australia": SYDNEY, "Melbourne, Australia": MELBOURNE}
        )
        self.calls: list[str] = []

    def geocode(self, place: str) -> GeoMatch | None:
        self.calls.append(place)
        return self.places.get(place)


class FakeTimezones:
    def __init__(self, zone: str | None = "Australia/Sydney") -> None:
        self.zone = zone
        self.calls: list[tuple[float, float]] = []

    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        self.calls.append((latitude, longitude))
        return self.zone


@pytest.fixture(scope="session")
def offline_geocoder() -> OfflineGeocoder:
    """The real bundled-data geocoder, loaded once per test run (about 3 seconds)."""
    geocoder = OfflineGeocoder(5000)
    geocoder.warm()
    return geocoder


@pytest.fixture
def geocoder() -> FakeGeocoder:
    return FakeGeocoder(
        {
            "Sydney, Australia": SYDNEY,
            "Melbourne, Australia": MELBOURNE,
            "Wellington, New Zealand": WELLINGTON,
        }
    )


@pytest.fixture
def timezones() -> FakeTimezones:
    return FakeTimezones()


@pytest.fixture
def client(geocoder: FakeGeocoder, timezones: FakeTimezones) -> Iterator[TestClient]:
    app = create_app(Settings(token=TOKEN), geocoder=geocoder, timezones=timezones)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample(client: TestClient) -> dict:
    response = client.post("/v1/chart", json=SAMPLE_REQUEST, headers=AUTH)
    assert response.status_code == 200, response.text
    return response.json()
