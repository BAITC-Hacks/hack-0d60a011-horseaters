"""Exact quantities that can be recorded without NUMERIC(18, 4) rounding."""

from decimal import Decimal, localcontext

def validate_quantity(value: Decimal, name: str, *, positive: bool = False) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal")
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    if positive and value == 0:
        raise ValueError(f"{name} must be positive")
    if value >= Decimal("100000000000000"):
        raise ValueError(f"{name} exceeds NUMERIC(18, 4)")
    with localcontext() as context:
        context.prec = 28
        if value != value.quantize(Decimal("0.0001")):
            raise ValueError(f"{name} must have at most four decimal places")
