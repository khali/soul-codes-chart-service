"""Human Design structural rules: type, authority and definition from channels."""

from __future__ import annotations

import pytest

from soulcodes_chart_service.hd.analysis import analyse, connected_groups, defined_channels
from soulcodes_chart_service.vendor.soulcodes_hd.center import CenterName


def gates_for(*channels: tuple[int, int]) -> set[int]:
    return {gate for channel in channels for gate in channel}


@pytest.mark.parametrize(
    ("channels", "expected_type", "expected_authority"),
    [
        # No channels: Reflector, Lunar.
        ((), "Reflector", "Lunar"),
        # Sacral only, no Throat: Generator.
        (((3, 60),), "Generator", "Sacral"),
        # Sacral to Throat directly (34-20): Manifesting Generator.
        (((20, 34),), "Manifesting Generator", "Sacral"),
        # Sacral to G (2-14) and G to Throat (1-8): motor reaches Throat indirectly.
        # Upstream soul-codes-hd only checked direct channels and called this a Generator.
        (((2, 14), (1, 8)), "Manifesting Generator", "Sacral"),
        # Heart to Throat (21-45): Manifestor, Ego Manifested.
        (((21, 45),), "Manifestor", "Ego Manifested"),
        # Heart to G (25-51) and G to Throat (7-31): Manifestor through the G centre.
        (((25, 51), (7, 31)), "Manifestor", "Ego Manifested"),
        # Heart to G only: Projector, Ego Projected.
        (((25, 51),), "Projector", "Ego Projected"),
        # G to Throat only: Projector, Self-Projected.
        (((10, 20),), "Projector", "Self-Projected"),
        # Head to Ajna to Throat: Projector, Mental.
        (((4, 63), (17, 62)), "Projector", "Mental"),
        # Solar Plexus to Throat (35-36): Manifestor, Emotional.
        (((35, 36),), "Manifestor", "Emotional (Solar Plexus)"),
        # Root to Spleen, Spleen to Throat: Root reaches Throat via Spleen.
        (((18, 58), (16, 48)), "Manifestor", "Splenic"),
        # Spleen to Throat only: Projector, Splenic (Spleen is not a motor).
        (((16, 48),), "Projector", "Splenic"),
        # Emotional authority outranks Sacral.
        (((6, 59),), "Generator", "Emotional (Solar Plexus)"),
    ],
)
def test_type_and_authority(channels: tuple, expected_type: str, expected_authority: str) -> None:
    structure = analyse(gates_for(*channels))
    assert structure.hd_type == expected_type
    assert structure.authority == expected_authority


@pytest.mark.parametrize(
    ("channels", "expected"),
    [
        ((), "No Definition"),
        (((4, 63), (17, 62)), "Single Definition"),
        (((4, 63), (32, 54)), "Split Definition"),
        (((4, 63), (32, 54), (25, 51)), "Triple Split Definition"),
        (((4, 63), (32, 54), (25, 51), (12, 22)), "Quadruple Split Definition"),
        # 27-50 joins Sacral and Spleen (upstream's definition table said Sacral/Root).
        (((27, 50), (3, 60), (32, 54)), "Single Definition"),
        (((27, 50), (18, 58)), "Single Definition"),
    ],
)
def test_definition(channels: tuple, expected: str) -> None:
    assert analyse(gates_for(*channels)).definition == expected


def test_hanging_gates_do_not_define_channels() -> None:
    assert defined_channels({1, 2, 3, 4, 5}) == []
    assert defined_channels({6, 59, 37}) == [(6, 59)]


def test_groups_are_connected_components() -> None:
    groups = connected_groups([(6, 59), (37, 40), (32, 54)])
    assert groups == [
        {CenterName.EGO, CenterName.SACRAL, CenterName.SOLAR_PLEXUS},
        {CenterName.SPLEEN, CenterName.ROOT},
    ]


def test_defined_centres_in_display_order() -> None:
    structure = analyse(gates_for((32, 54), (4, 63)))
    assert structure.defined_centres == [CenterName.HEAD, CenterName.AJNA, CenterName.SPLEEN, CenterName.ROOT]
