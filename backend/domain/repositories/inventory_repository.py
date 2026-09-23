from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.domain.entities.imports import (
    InventorySnapshot,
    InTransitItem,
    StockoutPeriod,
)


class InventoryRepository(Protocol):
    """Persistence port for stock, stockout and in-transit facts."""

    def add_snapshots(
        self, snapshots: Iterable[InventorySnapshot]
    ) -> Sequence[InventorySnapshot]: ...

    def get_latest_snapshot(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        as_of: datetime,
    ) -> InventorySnapshot | None: ...

    def list_snapshots(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        started_at: datetime,
        ended_at: datetime,
    ) -> Sequence[InventorySnapshot]: ...

    def add_stockout_periods(
        self, periods: Iterable[StockoutPeriod]
    ) -> Sequence[StockoutPeriod]: ...

    def list_stockout_periods(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        started_at: datetime,
        ended_at: datetime,
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
