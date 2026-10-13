"""Place-name normalisation for matching ("São Paulo" == "sao paulo", "Białystok" == "bialystok")."""

from __future__ import annotations

import re
import unicodedata

# Letters that Unicode decomposition does not reduce to ASCII.
_SPECIAL = str.maketrans(
    {"ł": "l", "ø": "o", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe", "ı": "i", "þ": "th", "ð": "d"}
)
_SEPARATORS = re.compile(r"[\s\-‐-―_/]+")
_DROPPED = re.compile(r"[.'’`]")
_LATIN = re.compile(r"^[a-z0-9 ]+$")


def normalise_name(text: str) -> str:
    """Lower-case ASCII form with accents removed and separators collapsed to spaces."""
    lowered = text.casefold().translate(_SPECIAL)
    decomposed = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = _DROPPED.sub("", stripped)
    return _SEPARATORS.sub(" ", stripped).strip()


def is_latin(normalised: str) -> bool:
    """True when a normalised name is plain ASCII letters, digits and spaces."""
    return bool(normalised) and bool(_LATIN.match(normalised))
