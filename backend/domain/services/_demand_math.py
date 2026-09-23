from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal


ZERO = Decimal("0")
ONE = Decimal("1")


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")
    return value.astimezone(timezone.utc)


def midnight(value: date) -> datetime:
    return datetime.combine(value, time(), tzinfo=timezone.utc)


def next_month(value: date) -> date:
    return date(value.year + value.month // 12, value.month % 12 + 1, 1)


def calendar(start: date, end: date, *, allow_partial_final_month: bool = False) -> tuple[tuple[date, date], ...]:
    if type(start) is not date or type(end) is not date:
        raise TypeError("Calendar bounds must be dates")
    if start.day != 1 or end < start or (not allow_partial_final_month and end + timedelta(days=1) != next_month(end)):
        raise ValueError("Use complete calendar months: first day through last day inclusive")
    periods = []
    while start <= end:
        following = next_month(start)
        periods.append((start, min(end, following - timedelta(days=1))))
        start = following
    return tuple(periods)


def quantile(values: list[Decimal], fraction: Decimal) -> Decimal:
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def median(values: list[Decimal]) -> Decimal:
    return quantile(values, Decimal("0.5"))


def days(delta: timedelta) -> Decimal:
    return (Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000) / 86400
