"""Exact NVC amount conversion helpers."""

from decimal import Decimal, InvalidOperation, ROUND_DOWN

from blockchain.protocol import ATOMIC_UNITS_PER_NVC


_ATOMIC = Decimal(ATOMIC_UNITS_PER_NVC)


def to_atomic_units(amount) -> int:
    """Convert an NVC amount to integer atomic units without float rounding."""
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError("Amount must be a valid decimal number.") from error
    if not value.is_finite() or value < 0:
        raise ValueError("Amount must be finite and non-negative.")
    scaled = (value * _ATOMIC).quantize(Decimal("1"), rounding=ROUND_DOWN)
    if value != scaled / _ATOMIC:
        raise ValueError("Amount has more than 8 decimal places.")
    return int(scaled)


def from_atomic_units(amount: int) -> Decimal:
    """Convert atomic units to an exact Decimal NVC amount."""
    if not isinstance(amount, int) or amount < 0:
        raise ValueError("Atomic amount must be a non-negative integer.")
    return Decimal(amount) / _ATOMIC


def format_nvc(amount: int) -> str:
    """Format atomic units for protocol/UI output without scientific notation."""
    return format(from_atomic_units(amount), "f")
