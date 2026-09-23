from collections.abc import Collection, Iterable, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.domain.entities.imports import InTransitItem, InventorySnapshot, StockoutPeriod


class InventoryRepository(Protocol):
    def get_latest_snapshot(
        self, product_id: UUID, warehouse_id: UUID, as_of: datetime, *,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> InventorySnapshot | None:
        """Latest snapshot_at <= as_of; raise AmbiguousSourceDataError on a tie."""
        ...

    def list_stockout_periods(
        self, start: datetime | UUID | None = None, end: datetime | UUID | None = None, *,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None, import_batch_ids: Collection[UUID] | None = None,
        started_at: datetime | None = None, ended_at: datetime | None = None,
    ) -> list[StockoutPeriod]:
        """Read completed-import or unbatched stockouts, including open intervals.

        REP-02: (start: datetime, end: datetime, *, product_id=..., warehouse_id=...)
        uses half-open intervals. Existing API: (product_id, warehouse_id,
        *, started_at, ended_at) uses inclusive boundaries. Keyword-only IDs also
        work with started_at/ended_at. Mixing the two forms is rejected.
        """
        ...

    def list_active_in_transit(
        self, *, product_id: UUID | None = None, warehouse_id: UUID | None = None,
        expected_from: datetime | None = None, expected_before: datetime | None = None,
        include_undated: bool = False, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[InTransitItem]:
        """planned/in_transit; expected_at in [from, before), plus NULL if requested."""
        ...

    def add_snapshots(
        self, snapshots: Iterable[InventorySnapshot]
    ) -> Sequence[InventorySnapshot]: ...

    def list_snapshots(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        started_at: datetime,
        ended_at: datetime,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> Sequence[InventorySnapshot]: ...

    def add_stockout_periods(
        self, periods: Iterable[StockoutPeriod]
    ) -> Sequence[StockoutPeriod]: ...

    def add_in_transit_items(
        self, items: Iterable[InTransitItem]
    ) -> Sequence[InTransitItem]: ...

    def list_open_in_transit(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        expected_by: datetime | None = None,
    ) -> Sequence[InTransitItem]: ...
