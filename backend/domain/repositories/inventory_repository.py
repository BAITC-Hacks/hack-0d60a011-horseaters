from collections.abc import Collection
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
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[StockoutPeriod]:
        """Intervals [started_at, ended_at) intersecting [start, end), NULL end is open."""
        ...

    def list_active_in_transit(
        self, *, product_id: UUID | None = None, warehouse_id: UUID | None = None,
        expected_from: datetime | None = None, expected_before: datetime | None = None,
        include_undated: bool = False, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[InTransitItem]:
        """planned/in_transit; expected_at in [from, before), plus NULL if requested."""
        ...
