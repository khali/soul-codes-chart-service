# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/core/calculation_engine.py
#   ChartCalculationEngine.__init__ (self.gate_order) and
#   ChartCalculationEngine._longitude_to_hd_data
# Changes:
#   - methods lifted to module-level functions (no class, no self)
#   - wrap-around uses modulo 360 instead of "if > 360: -= 360", so a longitude of
#     exactly 302.0 degrees maps to gate 41 instead of raising IndexError (upstream bug)
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""Map an ecliptic longitude onto the Human Design mandala (gate, line, colour, tone, base)."""

from __future__ import annotations

# Human Design gate order (I-Ching wheel), starting at Gate 41 = 302 degrees tropical.
GATE_ORDER: tuple[int, ...] = (
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42, 3,
    27, 24, 2, 23, 8, 20, 16, 35, 45, 12, 15, 52, 39, 53, 62, 56,
    31, 33, 7, 4, 29, 59, 40, 64, 47, 6, 46, 18, 48, 57, 32, 50,
    28, 44, 1, 43, 14, 34, 9, 5, 26, 11, 10, 58, 38, 54, 61, 60,
)  # fmt: skip

# The mandala starts 58 degrees before 0 Aries.
WHEEL_OFFSET_DEGREES = 58.0


def longitude_to_hd_data(longitude: float) -> tuple[int, int, int, int, int]:
    """Convert an ecliptic longitude to (gate, line, color, tone, base)."""
    celestial_position = (longitude + WHEEL_OFFSET_DEGREES) % 360.0
    percentage_through = celestial_position / 360.0

    gate = GATE_ORDER[int(percentage_through * 64)]
    line = int((384 * percentage_through) % 6) + 1
    color = int((2304 * percentage_through) % 6) + 1
    tone = int((13824 * percentage_through) % 6) + 1
    base = int((69120 * percentage_through) % 5) + 1
    return gate, line, color, tone, base
