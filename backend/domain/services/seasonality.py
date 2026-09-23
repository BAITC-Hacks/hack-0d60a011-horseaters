from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from uuid import UUID

from backend.domain.entities.imports import SeasonalityCoefficient


class AmbiguousSeasonalityError(ValueError):
    pass


def select_seasonality_index(
    coefficients: Iterable[SeasonalityCoefficient],
    *,
    product_id: UUID,
    category_id: UUID | None,
    on_date: date,
    version: int | None = None,
) -> Decimal:
    """Select an active SKU coefficient, falling back to its category and then 1."""
    active = [
        item
        for item in coefficients
        if item.month == on_date.month
        and item.valid_from <= on_date
        and (item.valid_to is None or item.valid_to >= on_date)
        and (version is None or item.version == version)
    ]
    product_matches = [item for item in active if item.product_id == product_id]
    selected = product_matches
    if not selected and category_id is not None:
        selected = [item for item in active if item.category_id == category_id]
    if not selected:
        return Decimal("1")
    if len(selected) > 1:
        raise AmbiguousSeasonalityError(
            "multiple active seasonality coefficients require an explicit version"
        )
    return selected[0].coefficient
