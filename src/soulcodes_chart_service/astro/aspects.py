"""Major aspects between planets, points and angles.

Orb allowances depend on what is involved. For a pair, the smaller of the two bodies'
allowances applies (so a Node never borrows the Sun's wide orb).

| class                          | conj | opp | trine | square | sextile |
|--------------------------------|------|-----|-------|--------|---------|
| luminary (Sun, Moon)           | 10   | 10  | 8     | 8      | 6       |
| planet (Mercury to Pluto)      | 8    | 8   | 7     | 7      | 5       |
| angle (Ascendant, Midheaven)   | 8    | 8   | 6     | 6      | 4       |
| point (Nodes, Chiron)          | 5    | 5   | 4     | 4      | 3       |

Pairs that are always in aspect by construction are skipped: North Node with South
Node, and Ascendant with Midheaven.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from .zodiac import separation

ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "trine": 120.0,
    "square": 90.0,
    "sextile": 60.0,
}

ORBS: dict[str, dict[str, float]] = {
    "luminary": {"conjunction": 10, "opposition": 10, "trine": 8, "square": 8, "sextile": 6},
    "planet": {"conjunction": 8, "opposition": 8, "trine": 7, "square": 7, "sextile": 5},
    "angle": {"conjunction": 8, "opposition": 8, "trine": 6, "square": 6, "sextile": 4},
    "point": {"conjunction": 5, "opposition": 5, "trine": 4, "square": 4, "sextile": 3},
}

_CLASSES = {
    "sun": "luminary",
    "moon": "luminary",
    "ascendant": "angle",
    "midheaven": "angle",
    "north_node": "point",
    "south_node": "point",
    "chiron": "point",
}

_SKIPPED_PAIRS = {frozenset({"north_node", "south_node"}), frozenset({"ascendant", "midheaven"})}


def body_class(key: str) -> str:
    return _CLASSES.get(key, "planet")


def orb_allowance(a: str, b: str, aspect: str) -> float:
    return min(ORBS[body_class(a)][aspect], ORBS[body_class(b)][aspect])


def aspect_between(a: str, lon_a: float, b: str, lon_b: float) -> dict[str, Any] | None:
    """The major aspect between two bodies, if any falls within orb."""
    if frozenset({a, b}) in _SKIPPED_PAIRS:
        return None
    angle = separation(lon_a, lon_b)
    for aspect, exact in ASPECT_ANGLES.items():
        orb = abs(angle - exact)
        if orb <= orb_allowance(a, b, aspect):
            return {"a": a, "b": b, "type": aspect, "orb": round(orb, 2)}
    return None


def find_aspects(longitudes: dict[str, float]) -> list[dict[str, Any]]:
    """All major aspects among the given bodies, tightest first.

    `longitudes` keeps insertion order, which fixes the a/b order in each aspect.
    """
    found = []
    for (a, lon_a), (b, lon_b) in combinations(longitudes.items(), 2):
        aspect = aspect_between(a, lon_a, b, lon_b)
        if aspect:
            found.append(aspect)
    return sorted(found, key=lambda item: item["orb"])
