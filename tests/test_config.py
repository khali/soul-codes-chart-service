"""Startup configuration: no token, no start (unless explicitly in local dev mode)."""

from __future__ import annotations

import pytest

from soulcodes_chart_service.app import create_app
from soulcodes_chart_service.config import ConfigError, load_settings

LONG_TOKEN = "a" * 40


def test_refuses_to_start_without_token() -> None:
    with pytest.raises(ConfigError, match="CHART_SERVICE_TOKEN is not set"):
        load_settings({})


def test_create_app_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHART_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHART_SERVICE_ALLOW_NO_AUTH", raising=False)
    with pytest.raises(ConfigError):
        create_app()


def test_token_from_environment() -> None:
    settings = load_settings({"CHART_SERVICE_TOKEN": f"  {LONG_TOKEN}  "})
    assert settings.token == LONG_TOKEN and settings.auth_required


def test_short_token_rejected() -> None:
    with pytest.raises(ConfigError, match="at least 32"):
        load_settings({"CHART_SERVICE_TOKEN": "short"})


def test_local_dev_without_auth() -> None:
    settings = load_settings({"CHART_SERVICE_ALLOW_NO_AUTH": "1"})
    assert settings.token is None and not settings.auth_required


@pytest.mark.parametrize("value", ["true", "yes", "0", ""])
def test_only_exact_one_disables_auth(value: str) -> None:
    with pytest.raises(ConfigError):
        load_settings({"CHART_SERVICE_ALLOW_NO_AUTH": value})


def test_geocoder_population_setting() -> None:
    env = {"CHART_SERVICE_TOKEN": LONG_TOKEN, "CHART_SERVICE_GEO_MIN_POPULATION": "15000"}
    assert load_settings(env).geo_min_population == 15000
    with pytest.raises(ConfigError):
        load_settings({**env, "CHART_SERVICE_GEO_MIN_POPULATION": "7"})
    with pytest.raises(ConfigError):
        load_settings({**env, "CHART_SERVICE_GEO_MIN_POPULATION": "lots"})
