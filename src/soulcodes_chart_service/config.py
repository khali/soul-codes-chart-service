"""Settings from environment variables. The service refuses to start without a token."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .geo.offline import SUPPORTED_POPULATIONS

MIN_TOKEN_LENGTH = 32


class ConfigError(RuntimeError):
    """Raised at startup when the environment is not safe to run with."""


@dataclass(frozen=True)
class Settings:
    token: str | None
    geo_min_population: int = 5000

    @property
    def auth_required(self) -> bool:
        return self.token is not None


def _population(env: Mapping[str, str]) -> int:
    raw = env.get("CHART_SERVICE_GEO_MIN_POPULATION", "5000")
    try:
        value = int(raw)
    except ValueError as err:
        raise ConfigError("CHART_SERVICE_GEO_MIN_POPULATION must be a number") from err
    if value not in SUPPORTED_POPULATIONS:
        raise ConfigError(f"CHART_SERVICE_GEO_MIN_POPULATION must be one of {SUPPORTED_POPULATIONS}")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Read settings; CHART_SERVICE_ALLOW_NO_AUTH=1 is for local development only."""
    env = os.environ if env is None else env
    token = env.get("CHART_SERVICE_TOKEN", "").strip() or None
    allow_no_auth = env.get("CHART_SERVICE_ALLOW_NO_AUTH") == "1"
    if token is None and not allow_no_auth:
        raise ConfigError(
            "CHART_SERVICE_TOKEN is not set. Set it to a long random secret "
            "(for example `openssl rand -hex 32`), or set CHART_SERVICE_ALLOW_NO_AUTH=1 "
            "for local development only."
        )
    if token is not None and len(token) < MIN_TOKEN_LENGTH:
        raise ConfigError(f"CHART_SERVICE_TOKEN must be at least {MIN_TOKEN_LENGTH} characters")
    return Settings(token=token, geo_min_population=_population(env))
