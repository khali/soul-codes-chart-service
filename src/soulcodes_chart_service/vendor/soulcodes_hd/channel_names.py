# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/data/reference.py (CHANNELS[*]["name"] only)
# Changes: extracted the 36 channel names into a gate-pair lookup; descriptions omitted.
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""Human Design channel names keyed by ascending gate pair."""

CHANNEL_NAMES: dict[tuple[int, int], str] = {
    (1, 8): 'Inspiration',
    (2, 14): 'The Beat',
    (3, 60): 'Mutation',
    (4, 63): 'Logic',
    (5, 15): 'Rhythm',
    (6, 59): 'Mating',
    (7, 31): 'The Alpha',
    (9, 52): 'Concentration',
    (10, 20): 'Awakening',
    (10, 34): 'Exploration',
    (10, 57): 'Perfected Form',
    (11, 56): 'Curiosity',
    (12, 22): 'Openness',
    (13, 33): 'The Prodigal',
    (16, 48): 'The Wavelength',
    (17, 62): 'Acceptance',
    (18, 58): 'Judgement',
    (19, 49): 'Synthesis',
    (20, 34): 'Charisma',
    (20, 57): 'The Brainwave',
    (21, 45): 'The Money Line',
    (23, 43): 'Structuring',
    (24, 61): 'Awareness',
    (25, 51): 'Initiation',
    (26, 44): 'Surrender',
    (27, 50): 'Preservation',
    (28, 38): 'Struggle',
    (29, 46): 'Discovery',
    (30, 41): 'Recognition',
    (32, 54): 'Transformation',
    (34, 57): 'Power',
    (35, 36): 'Transitoriness',
    (37, 40): 'Community',
    (39, 55): 'Emoting',
    (42, 53): 'Maturation',
    (47, 64): 'Abstraction',
}
