# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/domain/value_objects/center.py
# Changes: absolute import rewritten as relative
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""
Center value object handling canonical naming and legacy aliases.
"""

from __future__ import annotations

from enum import Enum

from .exceptions import InvalidCenterNameError

_ALIASES: dict[str, str] = {
    "g center": "G-Center",
    "g-center": "G-Center",
    "g": "G-Center",
    "identity": "G-Center",  # Identity Center is another name for G-Center
    "heart": "Ego",
    "heart/ego": "Ego",
    "heart/ego/will": "Ego",
    "heart center": "Ego",
    "heart center (ego)": "Ego",
    "will": "Ego",
    "will center": "Ego",
    "willpower": "Ego",
    "ego": "Ego",
    "emotional": "Solar Plexus",
    "solar plexus": "Solar Plexus",
    "emotions": "Solar Plexus",
    "ajna": "Ajna",
    "throat": "Throat",
    "head": "Head",
    "root": "Root",
    "spleen": "Spleen",
    "splenic": "Spleen",
    "sacral": "Sacral",
}


class CenterName(str, Enum):
    """
    Canonical Human Design center names.

    The underlying value keeps the historically-used label so that persisted
    payloads remain backward compatible. Use :meth:`normalize` to coerce legacy
    variants (e.g., "Heart", "G Center") into their canonical representation.
    """

    HEAD = "Head"
    AJNA = "Ajna"
    THROAT = "Throat"
    G_CENTER = "G-Center"
    EGO = "Ego"
    SACRAL = "Sacral"
    SOLAR_PLEXUS = "Solar Plexus"
    SPLEEN = "Spleen"
    ROOT = "Root"

    # Normalization aliases mapped via casefolded key.
    @classmethod
    def normalize(cls, name: str | CenterName) -> CenterName:
        """
        Normalize a center string (or enum) into a canonical :class:`CenterName`.

        Raises:
            InvalidCenterNameError: If the provided name cannot be normalized.
        """
        if isinstance(name, cls):
            return name

        if name is None:
            raise InvalidCenterNameError("None", [c.value for c in cls])

        candidate = str(name).strip()
        if not candidate:
            raise InvalidCenterNameError(candidate, [c.value for c in cls])

        direct_match = cls._try_direct_match(candidate)
        if direct_match:
            return direct_match

        alias_key = candidate.casefold()
        if alias_key in _ALIASES:
            return cls(_ALIASES[alias_key])

        valid_names = [c.value for c in cls] + sorted(_ALIASES)
        raise InvalidCenterNameError(candidate, valid_names)

    @classmethod
    def _try_direct_match(cls, value: str) -> CenterName | None:
        """Attempt to match the raw string directly to an enum member."""
        for center in cls:
            if value == center.value:
                return center
            if value.casefold() == center.value.casefold():
                return center
        return None

    def to_display(self) -> str:
        """
        Return the preferred display label for user-facing copy.

        Defaults to the canonical value unless a legacy label (e.g., "Heart")
        provides better UX context.
        """
        return _DISPLAY_NAMES.get(self, self.value)


def normalize_centers(names: list[str | CenterName]) -> set[CenterName]:
    """Normalize a list of center values into a set of canonical enums."""
    return {CenterName.normalize(name) for name in names}


def display_centers(centers: set[CenterName]) -> list[str]:
    """Convert a set of centers into their display labels."""
    return [center.to_display() for center in sorted(centers, key=lambda c: c.value)]


_DISPLAY_NAMES: dict[CenterName, str] = {
    CenterName.G_CENTER: "G Center",
    CenterName.EGO: "Heart",
}
