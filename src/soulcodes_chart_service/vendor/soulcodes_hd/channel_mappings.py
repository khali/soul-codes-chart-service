# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/domain/constants/channel_mappings.py
# Changes: absolute import rewritten as relative
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""
Channel-to-center mappings extracted from the legacy calculation engine.
"""

from __future__ import annotations

from collections.abc import Iterable

from .center import CenterName


def _normalize_centers(values: Iterable[str]) -> list[CenterName]:
    return [CenterName.normalize(value) for value in values]


CHANNEL_TO_CENTERS: dict[tuple[int, int], list[CenterName]] = {}

_RAW_CHANNELS: dict[tuple[int, int], tuple[str, str]] = {
    (1, 8): ("G", "Throat"),
    (2, 14): ("G", "Sacral"),
    (3, 60): ("Sacral", "Root"),
    (4, 63): ("Head", "Ajna"),
    (5, 15): ("Sacral", "G"),
    (6, 59): ("Solar Plexus", "Sacral"),
    (7, 31): ("G", "Throat"),
    (9, 52): ("Root", "Sacral"),
    (10, 20): ("G", "Throat"),
    (10, 34): ("G", "Sacral"),
    (10, 57): ("G", "Spleen"),
    (11, 56): ("Ajna", "Throat"),
    (12, 22): ("Throat", "Solar Plexus"),
    (13, 33): ("G", "Throat"),
    (16, 48): ("Throat", "Spleen"),
    (17, 62): ("Ajna", "Throat"),
    (18, 58): ("Root", "Spleen"),
    (19, 49): ("Root", "Solar Plexus"),
    (20, 34): ("Throat", "Sacral"),
    (20, 57): ("Throat", "Spleen"),
    (21, 45): ("Ego", "Throat"),
    (23, 43): ("Ajna", "Throat"),
    (24, 61): ("Ajna", "Head"),
    (25, 51): ("G", "Ego"),
    (26, 44): ("Ego", "Spleen"),
    (27, 50): ("Sacral", "Spleen"),
    (28, 38): ("Spleen", "Root"),
    (29, 46): ("Sacral", "G"),
    (30, 41): ("Solar Plexus", "Root"),
    (32, 54): ("Root", "Spleen"),
    (34, 57): ("Sacral", "Spleen"),
    (35, 36): ("Throat", "Solar Plexus"),
    (37, 40): ("Solar Plexus", "Ego"),
    (39, 55): ("Root", "Solar Plexus"),
    (42, 53): ("Root", "Sacral"),
    (47, 64): ("Ajna", "Head"),
    (50, 27): ("Spleen", "Sacral"),
    (53, 42): ("Root", "Sacral"),
    (54, 32): ("Root", "Spleen"),
    (57, 10): ("Spleen", "G"),
    (57, 20): ("Spleen", "Throat"),
    (58, 18): ("Root", "Spleen"),
    (59, 6): ("Sacral", "Solar Plexus"),
    (60, 3): ("Root", "Sacral"),
    (61, 24): ("Head", "Ajna"),
    (62, 17): ("Ajna", "Throat"),
    (63, 4): ("Head", "Ajna"),
    (64, 47): ("Head", "Ajna"),
}

for (gate_a, gate_b), centers in _RAW_CHANNELS.items():
    ordered = (min(gate_a, gate_b), max(gate_a, gate_b))
    CHANNEL_TO_CENTERS[ordered] = _normalize_centers(centers)

# Remove temporary variable from module namespace
del _RAW_CHANNELS
