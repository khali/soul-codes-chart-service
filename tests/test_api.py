"""HTTP API: auth, validation, error envelope and response shape."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from soulcodes_chart_service.app import create_app
from soulcodes_chart_service.config import Settings
from soulcodes_chart_service.geo.offline import GeoMatch

from .conftest import AMARA_REQUEST, AUTH, SAMPLE_REQUEST, TOKEN, FakeGeocoder, FakeTimezones


def _error(response) -> dict:
    body = response.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
    return body["error"]


class TestHealth:
    def test_no_auth_needed(self, client: TestClient) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert {"kerykeion", "pyswisseph", "soulcodes-hd", "tzdata"} <= set(body["engines"])


class TestAuth:
    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Authorization": TOKEN},
            {"Authorization": f"Basic {TOKEN}"},
            {"Authorization": "Bearer "},
            {"Authorization": f"Bearer {TOKEN}x"},
            {"Authorization": "Bearer wrong"},
        ],
    )
    def test_rejects_missing_or_wrong_token(self, client: TestClient, headers: dict) -> None:
        response = client.post("/v1/chart", json=SAMPLE_REQUEST, headers=headers)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert _error(response)["code"] == "unauthorized"

    def test_auth_checked_before_validation(self, client: TestClient) -> None:
        response = client.post("/v1/chart", json={"nonsense": True})
        assert response.status_code == 401

    def test_scheme_is_case_insensitive(self, client: TestClient) -> None:
        response = client.post("/v1/chart", json=SAMPLE_REQUEST, headers={"Authorization": f"bearer {TOKEN}"})
        assert response.status_code == 200

    def test_no_auth_mode(self) -> None:
        app = create_app(Settings(token=None), geocoder=FakeGeocoder(), timezones=FakeTimezones())
        with TestClient(app) as open_client:
            assert open_client.post("/v1/chart", json=SAMPLE_REQUEST).status_code == 200


class TestValidation:
    @pytest.mark.parametrize(
        ("change", "field"),
        [
            ({"date": "04/07/1985"}, "date"),
            ({"date": "1985-02-30"}, "date"),
            ({"date": "1800-12-31"}, "date"),
            ({"date": "2399-12-31"}, "date"),
            ({"date": 19850704}, "date"),
            ({"time": "3:00"}, "time"),
            ({"time": "24:00"}, "time"),
            ({"name": "   "}, "name"),
            ({"place": ""}, "place"),
            ({"latitude": 91.0, "longitude": 0.0}, "latitude"),
            ({"latitude": -33.8}, "latitude and longitude"),
            ({"timezone": "Sydney"}, "timezone"),
        ],
    )
    def test_invalid_fields(self, client: TestClient, change: dict, field: str) -> None:
        response = client.post("/v1/chart", json={**SAMPLE_REQUEST, **change}, headers=AUTH)
        assert response.status_code == 422
        error = _error(response)
        assert error["code"] == "invalid_request"
        assert field in error["message"]

    def test_missing_fields(self, client: TestClient) -> None:
        response = client.post("/v1/chart", json={"name": "Amara"}, headers=AUTH)
        assert response.status_code == 422
        assert "date" in _error(response)["message"]

    def test_malformed_json(self, client: TestClient) -> None:
        response = client.post(
            "/v1/chart", content=b"{not json", headers={**AUTH, "Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert _error(response)["code"] == "bad_request"

    def test_unknown_place(self, client: TestClient) -> None:
        response = client.post("/v1/chart", json={**SAMPLE_REQUEST, "place": "Atlantis"}, headers=AUTH)
        assert response.status_code == 422
        assert _error(response)["code"] == "place_not_found"

    def test_ambiguous_place_is_guessed_with_a_warning_unless_refusal_is_requested(
        self, geocoder: FakeGeocoder, timezones: FakeTimezones
    ) -> None:
        geocoder.places["Wellington"] = GeoMatch(
            "Wellington", "NZ", -41.28664, 174.77557, "Pacific/Auckland", ambiguous=True
        )
        app = create_app(Settings(token=TOKEN), geocoder=geocoder, timezones=timezones)
        body = {**AMARA_REQUEST, "place": "Wellington"}
        with TestClient(app) as client:
            guessed = client.post("/v1/chart", json=body, headers=AUTH)
            assert guessed.status_code == 200
            assert any(
                "More than one place is called Wellington" in w for w in guessed.json()["meta"]["warnings"]
            )

            refused = client.post("/v1/chart", json={**body, "rejectAmbiguousPlace": True}, headers=AUTH)
            assert refused.status_code == 422
            assert _error(refused)["code"] == "place_ambiguous"

            with_country = client.post(
                "/v1/chart",
                json={**AMARA_REQUEST, "rejectAmbiguousPlace": True},
                headers=AUTH,
            )
            assert with_country.status_code == 200

    def test_timezone_name_is_canonicalised(self, client: TestClient) -> None:
        body = {**SAMPLE_REQUEST, "latitude": -33.87, "longitude": 151.21, "timezone": "australia/sydney"}
        response = client.post("/v1/chart", json=body, headers=AUTH)
        assert response.status_code == 200
        assert response.json()["birth"]["timezone"] == "Australia/Sydney"


class TestErrors:
    def test_unknown_route_uses_envelope(self, client: TestClient) -> None:
        response = client.get("/nope")
        assert response.status_code == 404
        assert _error(response)["code"] == "not_found"

    def test_wrong_method_uses_envelope(self, client: TestClient) -> None:
        response = client.get("/v1/chart", headers=AUTH)
        assert response.status_code == 405
        assert _error(response)["code"] == "method_not_allowed"

    def test_unexpected_failure_hides_details(self) -> None:
        class BrokenGeocoder:
            def geocode(self, place: str) -> None:
                raise RuntimeError("secret internals")

        app = create_app(Settings(token=TOKEN), geocoder=BrokenGeocoder(), timezones=FakeTimezones())
        with TestClient(app, raise_server_exceptions=False) as broken:
            response = broken.post("/v1/chart", json=SAMPLE_REQUEST, headers=AUTH)
        assert response.status_code == 500
        error = _error(response)
        assert error == {"code": "internal_error", "message": "The chart could not be calculated."}


class TestChart:
    def test_coordinates_override_geocoding(self, client: TestClient, geocoder: FakeGeocoder) -> None:
        body = {**SAMPLE_REQUEST, "latitude": -33.87, "longitude": 151.21, "timezone": "Australia/Sydney"}
        response = client.post("/v1/chart", json=body, headers=AUTH)
        assert response.status_code == 200
        assert geocoder.calls == []
        assert response.json()["birth"]["latitude"] == -33.87

    def test_camel_case_keys(self, sample: dict) -> None:
        assert set(sample) == {"version", "birth", "astrology", "humanDesign", "meta"}
        assert {"timeKnown", "utcDateTime"} <= set(sample["birth"])
        assert {"houseSystem", "bigThree"} <= set(sample["astrology"])
        assert {"incarnationCross", "notSelfTheme", "definedCenters"} <= set(sample["humanDesign"])
        assert set(sample["meta"]) == {"calculatedAt", "engines", "warnings"}
        assert sample["meta"]["calculatedAt"].endswith("Z")

    def test_unknown_time(self, client: TestClient) -> None:
        response = client.post("/v1/chart", json=AMARA_REQUEST, headers=AUTH)
        assert response.status_code == 200
        chart = response.json()
        assert chart["humanDesign"] is None
        assert chart["birth"]["timeKnown"] is False and chart["birth"]["time"] is None
        # Wellington, 14 March 1988 midday NZST (UTC+12; summer time ended 6 March).
        assert chart["birth"]["utcDateTime"] == "1988-03-14T00:00:00Z"
        astrology = chart["astrology"]
        assert astrology["houses"] is None and astrology["angles"] is None
        assert astrology["bigThree"]["ascendant"] is None
        warnings = chart["meta"]["warnings"]
        assert any("Human Design" in w for w in warnings)
        assert any("Moon" in w for w in warnings)
        assert all("—" not in w for w in warnings)
