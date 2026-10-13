"""Human Design structure: channels, centres, type, authority and definition.

Rules follow the standard Human Design system (Ra Uru Hu / Jovian Archive):

* A channel is defined when both of its gates are activated (personality or design).
* A centre is defined when it sits at either end of a defined channel.
* Type: no defined centres is a Reflector. A defined Sacral is a Generator, or a
  Manifesting Generator when a motor reaches the Throat. Otherwise a Manifestor when a
  motor (Solar Plexus, Heart, Root) reaches the Throat, else a Projector.
  "Reaches" means connected through any chain of defined channels, not only directly.
* Authority hierarchy: Solar Plexus, Sacral, Spleen, Heart (Ego), G (Self-Projected),
  then Mental for Projectors; Reflectors are Lunar.
* Definition is the number of separate groups of connected defined centres.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..vendor.soulcodes_hd.center import CenterName
from ..vendor.soulcodes_hd.channel_mappings import CHANNEL_TO_CENTERS
from ..vendor.soulcodes_hd.gate_mappings import GATE_TO_CENTER

# Contract keys (packages/chart-types HdCenter) in canonical display order.
CENTRE_KEYS: dict[CenterName, str] = {
    CenterName.HEAD: "head",
    CenterName.AJNA: "ajna",
    CenterName.THROAT: "throat",
    CenterName.G_CENTER: "g",
    CenterName.EGO: "heart",
    CenterName.SACRAL: "sacral",
    CenterName.SOLAR_PLEXUS: "solar_plexus",
    CenterName.SPLEEN: "spleen",
    CenterName.ROOT: "root",
}
_CENTRE_ORDER = list(CENTRE_KEYS)

_MOTORS_EXCEPT_SACRAL = frozenset({CenterName.SOLAR_PLEXUS, CenterName.EGO, CenterName.ROOT})
_ALL_MOTORS = _MOTORS_EXCEPT_SACRAL | {CenterName.SACRAL}

DEFINITION_LABELS = {
    0: "No Definition",
    1: "Single Definition",
    2: "Split Definition",
    3: "Triple Split Definition",
    4: "Quadruple Split Definition",
}

Channel = tuple[int, int]


@dataclass(frozen=True)
class Structure:
    """The structural reading of a bodygraph."""

    channels: list[Channel]
    defined_centres: list[CenterName]
    hd_type: str
    authority: str
    definition: str


def defined_channels(gates: Iterable[int]) -> list[Channel]:
    """Channels whose two gates are both activated, sorted by gate pair."""
    active = set(gates)
    return sorted(pair for pair in CHANNEL_TO_CENTERS if pair[0] in active and pair[1] in active)


def channel_centres(channel: Channel) -> tuple[CenterName, CenterName]:
    """The two centres of a channel, in the same order as its gates."""
    return GATE_TO_CENTER[channel[0]], GATE_TO_CENTER[channel[1]]


def connected_groups(channels: Iterable[Channel]) -> list[set[CenterName]]:
    """Groups of defined centres joined by defined channels (graph components)."""
    adjacency: dict[CenterName, set[CenterName]] = {}
    for channel in channels:
        a, b = channel_centres(channel)
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    groups: list[set[CenterName]] = []
    seen: set[CenterName] = set()
    for start in sorted(adjacency, key=_CENTRE_ORDER.index):
        if start in seen:
            continue
        group = _walk(start, adjacency)
        seen |= group
        groups.append(group)
    return groups


def _walk(start: CenterName, adjacency: dict[CenterName, set[CenterName]]) -> set[CenterName]:
    group = {start}
    frontier = [start]
    while frontier:
        for neighbour in adjacency[frontier.pop()]:
            if neighbour not in group:
                group.add(neighbour)
                frontier.append(neighbour)
    return group


def _motor_reaches_throat(groups: list[set[CenterName]], motors: frozenset[CenterName]) -> bool:
    return any(CenterName.THROAT in group and group & motors for group in groups)


def determine_type(groups: list[set[CenterName]]) -> str:
    centres = set().union(*groups) if groups else set()
    if not centres:
        return "Reflector"
    if CenterName.SACRAL in centres:
        if _motor_reaches_throat(groups, _ALL_MOTORS):
            return "Manifesting Generator"
        return "Generator"
    if _motor_reaches_throat(groups, _MOTORS_EXCEPT_SACRAL):
        return "Manifestor"
    return "Projector"


def determine_authority(hd_type: str, centres: set[CenterName]) -> str:
    if hd_type == "Reflector":
        return "Lunar"
    if CenterName.SOLAR_PLEXUS in centres:
        return "Emotional (Solar Plexus)"
    if CenterName.SACRAL in centres:
        return "Sacral"
    if CenterName.SPLEEN in centres:
        return "Splenic"
    if CenterName.EGO in centres:
        return "Ego Manifested" if hd_type == "Manifestor" else "Ego Projected"
    if CenterName.G_CENTER in centres:
        return "Self-Projected"
    return "Mental"


def analyse(gates: Iterable[int]) -> Structure:
    """Derive the full structure of a bodygraph from its activated gates."""
    channels = defined_channels(gates)
    groups = connected_groups(channels)
    centres = set().union(*groups) if groups else set()
    hd_type = determine_type(groups)
    return Structure(
        channels=channels,
        defined_centres=sorted(centres, key=_CENTRE_ORDER.index),
        hd_type=hd_type,
        authority=determine_authority(hd_type, centres),
        definition=DEFINITION_LABELS[len(groups)],
    )
