from collections.abc import Collection
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from backend.domain.entities.imports import MonthlySales, SalesTransaction
from backend.domain.enums import TransactionType
from .filters import ALL, IdFilter


class SalesRepository(Protocol):
    def get_transactions_by_ids(
        self, transaction_ids: Collection[UUID], *, as_of: datetime,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SalesTransaction]:
        """Completed-import facts known at the inclusive timestamp cutoff."""
        ...

    def list_returns_for_sales(
        self, sale_ids: Collection[UUID], *, as_of: datetime,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SalesTransaction]:
        """Linked returns through as_of, including returns outside the sale's month."""
        ...

    def list_transactions(
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None, transaction_type: TransactionType | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SalesTransaction]:
        """Raw sales/returns with sold_at in [start, end), from completed imports."""
        ...

    def list_monthly_sales(
        self, start: date, end: date, *, product_id: UUID | None = None,
        warehouse_id: IdFilter = ALL, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[MonthlySales]:
        """Whole aggregate rows overlapping inclusive [start, end]; never prorated.

        warehouse_id=None selects only rows without a warehouse, ALL selects all.
        """
        ...
