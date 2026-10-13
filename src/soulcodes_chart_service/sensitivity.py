"""Warn when a slightly different birth time would change the headline results.

Recorded birth times are often rounded, so the chart is recalculated 15 minutes either
side. If the sign of a planet or the Ascendant, or a Human Design headline (type,
authority, profile, definition, incarnation cross) would change, the reading should hold
it more lightly.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .astro.calculator import julian_day_ut, planet_positions
from .astro.houses import calculate_houses
from .astro.uncertainty import BODY_LABELS
from .astro.zodiac import SIGN_LABELS, sign_of
from .hd.calculator import HumanDesignResult
from .hd.calculator import calculate as calculate_hd

WINDOW = timedelta(minutes=15)

_HD_FIELDS = (
    ("type", lambda r: r.structure.hd_type),
    ("authority", lambda r: r.structure.authority),
    ("profile", lambda r: r.profile),
    ("definition", lambda r: r.structure.definition),
    ("incarnation cross", lambda r: r.incarnation_cross),
)


def _ascendant_sign(moment: datetime, lat: float, lng: float) -> str:
    return sign_of(calculate_houses(julian_day_ut(moment), lat, lng).ascendant)


def ascendant_warning(moment: datetime, lat: float, lng: float) -> str | None:
    offsets = (-WINDOW, timedelta(0), WINDOW)
    signs = [_ascendant_sign(moment + offset, lat, lng) for offset in offsets]
    if len(set(signs)) == 1:
        return None
    return _edge_message("The Ascendant", signs[1], set(signs) - {signs[1]})


def _edge_message(subject: str, current: str, others: set[str]) -> str:
    alternatives = " or ".join(sorted(SIGN_LABELS[sign] for sign in others))
    return (
        f"{subject} is at the very edge of {SIGN_LABELS[current]}: a birth time 15 minutes "
        f"different would put it in {alternatives}."
    )


def planet_sign_warnings(moment: datetime, lat: float, lng: float) -> list[str]:
    """One warning per planet whose sign differs 15 minutes either side (South Node mirrors North)."""
    offsets = (-WINDOW, timedelta(0), WINDOW)
    before, now, after = (planet_positions(moment + offset, lat, lng) for offset in offsets)
    warnings = []
    for early, body, late in zip(before, now, after, strict=True):
        current = sign_of(body.longitude)
        others = {sign_of(early.longitude), sign_of(late.longitude)} - {current}
        if others and body.key != "south_node":
            label = BODY_LABELS[body.key]
            warnings.append(_edge_message(label[0].upper() + label[1:], current, others))
    return warnings


def human_design_warning(moment: datetime, base: HumanDesignResult) -> str | None:
    neighbours = [calculate_hd(moment - WINDOW), calculate_hd(moment + WINDOW)]
    changed = [
        label for label, value in _HD_FIELDS if any(value(other) != value(base) for other in neighbours)
    ]
    if not changed:
        return None
    listed = changed[0] if len(changed) == 1 else f"{', '.join(changed[:-1])} and {changed[-1]}"
    return (
        f"A birth time 15 minutes different would change the Human Design {listed}, "
        "so these rest on the recorded time being accurate."
    )
