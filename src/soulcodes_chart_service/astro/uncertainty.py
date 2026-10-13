"""Warnings about what an unknown birth time leaves uncertain."""

from __future__ import annotations

from .calculator import BodyPosition
from .zodiac import SIGN_LABELS, sign_of

BODY_LABELS: dict[str, str] = {
    "sun": "the Sun",
    "moon": "the Moon",
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluto": "Pluto",
    "north_node": "the North Node",
    "south_node": "the South Node",
    "chiron": "Chiron",
}

NO_TIME_WARNING = (
    "Birth time unknown: the chart is calculated for midday, so houses, angles and the "
    "Ascendant are left out."
)


def _sign_label(longitude: float) -> str:
    return SIGN_LABELS[sign_of(longitude)]


def sign_change_warnings(
    start: list[BodyPosition], midday: list[BodyPosition], end: list[BodyPosition]
) -> list[str]:
    """One warning for the Moon, plus one for any other body that changed sign that day."""
    warnings = []
    for first, noon, last in zip(start, midday, end, strict=True):
        label = BODY_LABELS[first.key]
        start_sign, end_sign = _sign_label(first.longitude), _sign_label(last.longitude)
        if start_sign != end_sign:
            warnings.append(
                f"Birth time unknown: {label} moved from {start_sign} into {end_sign} that "
                f"day, so either sign is possible. It is shown at midday, in "
                f"{_sign_label(noon.longitude)}."
            )
        elif first.key == "moon":
            warnings.append(
                f"Birth time unknown: the Moon moves about 13 degrees a day, so its exact "
                f"degree is uncertain. It stayed in {start_sign} all day."
            )
    return warnings
