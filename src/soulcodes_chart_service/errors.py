"""The service's error type and the `{ "error": { "code", "message" } }` envelope."""

from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """An error with a stable machine code, a readable message and an HTTP status."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class PlaceNotFound(ServiceError):
    def __init__(self, place: str) -> None:
        super().__init__(
            422,
            "place_not_found",
            f"We could not find '{place}'. Try adding the country, or send latitude, "
            "longitude and timezone instead.",
        )


class TimezoneNotFound(ServiceError):
    def __init__(self) -> None:
        super().__init__(
            422,
            "timezone_not_found",
            "We could not work out the time zone for these coordinates. Please send a "
            "timezone such as 'Australia/Sydney'.",
        )


def envelope(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}
