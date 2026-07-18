"""Calculation-specific exceptions."""


class CalculationError(ValueError):
    """Base for all calculation errors."""


class InvalidDecimalError(CalculationError):
    """Raised when a value cannot be converted to a valid finite Decimal."""


class DivisionUndefinedError(CalculationError):
    """Raised when a required division has a zero denominator."""
