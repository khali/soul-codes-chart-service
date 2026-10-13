"""Human Design chart for a birth moment, shaped like the HumanDesignChart contract type."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..vendor.soulcodes_hd.channel_names import CHANNEL_NAMES
from ..vendor.soulcodes_hd.crosses import calculate_incarnation_cross
from ..vendor.soulcodes_hd.ephemeris import calculate_planetary_positions, find_design_date
from ..vendor.soulcodes_hd.wheel import longitude_to_hd_data
from .analysis import CENTRE_KEYS, Structure, analyse, channel_centres
from .labels import NOT_SELF_THEME, SIGNATURE, STRATEGY

# Engine planet name -> contract HdPlanet key, in bodygraph display order.
HD_PLANET_KEYS: dict[str, str] = {
    "Sun": "sun",
    "Earth": "earth",
    "Moon": "moon",
    "North Node": "north_node",
    "South Node": "south_node",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
    "Uranus": "uranus",
    "Neptune": "neptune",
    "Pluto": "pluto",
}


@dataclass(frozen=True)
class Activation:
    planet: str
    longitude: float
    gate: int
    line: int


@dataclass(frozen=True)
class HumanDesignResult:
    """Everything calculated, before shaping into the contract payload."""

    personality: list[Activation]
    design: list[Activation]
    design_moment: datetime
    structure: Structure
    profile: str
    incarnation_cross: str


def _activations(positions: dict[str, float]) -> list[Activation]:
    result = []
    for engine_name, key in HD_PLANET_KEYS.items():
        longitude = positions[engine_name]
        gate, line, _color, _tone, _base = longitude_to_hd_data(longitude)
        result.append(Activation(planet=key, longitude=longitude, gate=gate, line=line))
    return result


def _find(activations: list[Activation], planet: str) -> Activation:
    return next(a for a in activations if a.planet == planet)


def _cross(personality: list[Activation], design: list[Activation]) -> str:
    p_sun, p_earth = _find(personality, "sun"), _find(personality, "earth")
    d_sun, d_earth = _find(design, "sun"), _find(design, "earth")
    return calculate_incarnation_cross(
        p_sun.line, d_sun.line, p_sun.gate, d_sun.gate, p_earth.gate, d_earth.gate
    )


def calculate(birth_moment: datetime) -> HumanDesignResult:
    """Calculate a Human Design chart for a timezone-aware birth moment."""
    design_moment = find_design_date(birth_moment)
    personality = _activations(calculate_planetary_positions(birth_moment))
    design = _activations(calculate_planetary_positions(design_moment))
    gates = {a.gate for a in personality} | {a.gate for a in design}
    profile = f"{_find(personality, 'sun').line}/{_find(design, 'sun').line}"
    return HumanDesignResult(
        personality=personality,
        design=design,
        design_moment=design_moment,
        structure=analyse(gates),
        profile=profile,
        incarnation_cross=_cross(personality, design),
    )


def to_payload(result: HumanDesignResult) -> dict[str, Any]:
    """Shape a result as the HumanDesignChart contract (snake_case attribute names)."""
    structure = result.structure
    hd_type = structure.hd_type
    return {
        "type": hd_type,
        "strategy": STRATEGY[hd_type],
        "authority": structure.authority,
        "profile": result.profile,
        "definition": structure.definition,
        "incarnation_cross": result.incarnation_cross,
        "signature": SIGNATURE[hd_type],
        "not_self_theme": NOT_SELF_THEME[hd_type],
        "defined_centers": [CENTRE_KEYS[c] for c in structure.defined_centres],
        "channels": [_channel_payload(channel) for channel in structure.channels],
        "activations": {
            "personality": [_activation_payload(a) for a in result.personality],
            "design": [_activation_payload(a) for a in result.design],
        },
    }


def _channel_payload(channel: tuple[int, int]) -> dict[str, Any]:
    first, second = channel_centres(channel)
    return {
        "gates": [channel[0], channel[1]],
        "name": CHANNEL_NAMES[channel],
        "centers": [CENTRE_KEYS[first], CENTRE_KEYS[second]],
    }


def _activation_payload(activation: Activation) -> dict[str, Any]:
    return {"planet": activation.planet, "gate": activation.gate, "line": activation.line}
