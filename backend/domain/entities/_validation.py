"""Local value checks; no database lookups or persistence dependencies."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum


def decimal_value(value: Decimal, name: str, *, minimum: Decimal | None = None) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def positive_decimal(value: Decimal, name: str) -> None:
    decimal_value(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def aware_datetime(value: datetime, name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")


def calendar_date(value: date, name: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be date without time")


def enum_value(value: Enum, enum_class: type[Enum], name: str) -> None:
    if not isinstance(value, enum_class):
        raise TypeError(f"{name} must be {enum_class.__name__}")
