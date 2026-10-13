# Vendored from the private soul-codes-hd repository @ 46ff24d5806e545ea136277a021dce9a02215550
# Source: soulcodes/domain/exceptions.py
# Changes: none (verbatim)
# Do not edit by hand without recording the change here; see vendor/soulcodes_hd/__init__.py.
"""
Domain-specific exceptions shared across Human Design calculations.

These exceptions prevent lower-level implementation details from leaking across
layers and make failures easier to reason about during debugging.
"""


class DomainException(Exception):
    """Base exception for all domain layer errors."""


class InvalidCenterNameError(DomainException):
    """
    Raised when a center name cannot be normalized to a canonical value.

    Attributes:
        name: The original invalid input.
        valid_names: All accepted canonical names and aliases.
    """

    def __init__(self, name: str, valid_names: list[str]):
        self.name = name
        self.valid_names = valid_names
        super().__init__(
            f"Invalid center name: '{name}'. "
            f"Valid names: {', '.join(sorted(valid_names))}"
        )


class InvalidGateNumberError(DomainException):
    """
    Raised when a provided gate number falls outside the valid Human Design range.
    """

    def __init__(self, gate: int):
        self.gate = gate
        super().__init__(
            f"Invalid gate number: {gate}. Gates must be between 1 and 64 (inclusive)."
        )


class InvalidAuthorityError(DomainException):
    """
    Raised when an authority cannot be determined from a set of centers.

    This indicates a data integrity error because the calculation engine should
    always provide a consistent set of centers.
    """

    def __init__(self, centers: set[str]):
        self.centers = centers
        super().__init__(
            f"Cannot determine authority from centers: {centers}. "
            "This indicates a data integrity issue."
        )
