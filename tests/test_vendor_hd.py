"""Integrity checks on the vendored Human Design tables and wheel maths."""

from __future__ import annotations

import re
from collections import defaultdict

import pytest

from soulcodes_chart_service.hd.analysis import channel_centres
from soulcodes_chart_service.vendor.soulcodes_hd.channel_mappings import CHANNEL_TO_CENTERS
from soulcodes_chart_service.vendor.soulcodes_hd.channel_names import CHANNEL_NAMES
from soulcodes_chart_service.vendor.soulcodes_hd.crosses import (
    JUXTAPOSITION_CROSSES,
    LEFT_ANGLE_CROSSES,
    RIGHT_ANGLE_CROSSES,
    calculate_incarnation_cross,
)
from soulcodes_chart_service.vendor.soulcodes_hd.gate_mappings import GATE_TO_CENTER
from soulcodes_chart_service.vendor.soulcodes_hd.wheel import GATE_ORDER, longitude_to_hd_data

OPPOSITE = {GATE_ORDER[i]: GATE_ORDER[(i + 32) % 64] for i in range(64)}


def test_wheel_has_every_gate_once() -> None:
    assert sorted(GATE_ORDER) == list(range(1, 65))


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (302.0, (41, 1)),  # start of the mandala; upstream raised IndexError here
        (301.99999, (60, 6)),
        (0.0, (25, 2)),  # gate 25 starts at 28°15' Pisces, so 0 Aries is line 2
        (340.5, (37, 6)),  # mid-Pisces
        (359.99999, (25, 2)),
        (358.25, (25, 1)),
    ],
)
def test_longitude_to_gate_and_line(longitude: float, expected: tuple[int, int]) -> None:
    gate, line, color, tone, base = longitude_to_hd_data(longitude)
    assert (gate, line) == expected
    assert 1 <= color <= 6 and 1 <= tone <= 6 and 1 <= base <= 5


def test_each_gate_spans_5_625_degrees() -> None:
    for index, gate in enumerate(GATE_ORDER):
        start = (302.0 + index * 5.625) % 360
        assert longitude_to_hd_data(start + 0.0001)[0] == gate
        assert longitude_to_hd_data(start + 5.6249)[0] == gate


def test_channel_tables_agree() -> None:
    assert len(CHANNEL_TO_CENTERS) == 36
    assert set(CHANNEL_NAMES) == set(CHANNEL_TO_CENTERS)
    for channel, centres in CHANNEL_TO_CENTERS.items():
        assert set(channel_centres(channel)) == set(centres), channel
    assert set(GATE_TO_CENTER) == set(range(1, 65))


@pytest.mark.parametrize(("table", "quarters"), [(RIGHT_ANGLE_CROSSES, 4), (LEFT_ANGLE_CROSSES, 2)])
def test_cross_families_are_complete(table: dict[int, str], quarters: int) -> None:
    """Each family names each quarter once, over gates closed under opposition.

    This caught upstream listing gate 51 as "Penetration 2" alongside gate 53.
    """
    families: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for gate, name in table.items():
        match = re.fullmatch(r"(.*?)(?: (\d))?", name)
        assert match
        families[match.group(1)].append((int(match.group(2) or 1), gate))
    for family, members in families.items():
        assert sorted(q for q, _ in members) == list(range(1, quarters + 1)), family
        gates = {g for _, g in members}
        assert all(OPPOSITE[g] in gates for g in gates), family


def test_cross_tables_cover_all_gates() -> None:
    for table in (RIGHT_ANGLE_CROSSES, LEFT_ANGLE_CROSSES, JUXTAPOSITION_CROSSES):
        assert set(table) == set(range(1, 65))


@pytest.mark.parametrize(
    ("lines", "angle"),
    [((4, 6), "Right Angle"), ((1, 3), "Right Angle"), ((4, 1), "Juxtaposition"), ((5, 1), "Left Angle")],
)
def test_cross_angle_follows_profile(lines: tuple[int, int], angle: str) -> None:
    name = calculate_incarnation_cross(lines[0], lines[1], 36, 11, 6, 12)
    assert name.startswith(f"{angle} Cross of ")
    assert name.endswith("(36/6 | 11/12)")
