from collections.abc import Collection
from datetime import date
from typing import Protocol
from uuid import UUID

from backend.domain.entities.imports import GrowthAssumption, SeasonalityCoefficient
from backend.domain.enums import GrowthSource
from .filters import ALL, IdFilter


class SeasonalityRepository(Protocol):
    def list_coefficients(
        self, product_id: UUID, on_date: date, *, version: int | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SeasonalityCoefficient]:
        """Valid coefficients for on_date.month; SKU takes priority over its category.

        Returns all candidates at the winning level, without choosing a version.
        """
        ...

    def get_coefficient(
        self, product_id: UUID, on_date: date, *, version: int | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> SeasonalityCoefficient | None:
        """Return the only candidate, None, or raise AmbiguousSourceDataError."""
        ...

    def list_growth_assumptions(
        self, on_date: date, *, product_id: IdFilter = ALL, category_id: IdFilter = ALL,
        warehouse_id: IdFilter = ALL, source: GrowthSource | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[GrowthAssumption]:
        """Exact AND filters, NULL via None; no SKU/category/warehouse/source priority.

        Validity is inclusive. Records without a batch are included unless an
        explicit batch whitelist is supplied (then only that whitelist is used).
        """
        ...
