from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select

from backend.domain.entities.imports import InTransitItem, InventorySnapshot, StockoutPeriod
from backend.domain.enums import TransitStatus
from backend.domain.repositories.filters import AmbiguousSourceDataError
from backend.domain.repositories.inventory_repository import InventoryRepository
from ._read_repository import SqlAlchemyReadRepository, time_range, utc, visible_import
from .models.imports import InTransitItemModel, InventorySnapshotModel, StockoutPeriodModel


class SqlAlchemyInventoryRepository(SqlAlchemyReadRepository, InventoryRepository):
    def get_latest_snapshot(
        self, product_id: UUID, warehouse_id: UUID, as_of: datetime, *,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> InventorySnapshot | None:
        model = InventorySnapshotModel
        query = select(model).where(
            model.product_id == product_id, model.warehouse_id == warehouse_id,
            model.snapshot_at <= utc(as_of), visible_import(model.import_batch_id, import_batch_ids),
        ).order_by(model.snapshot_at.desc(), model.id).limit(2)
        rows = self._read(query, InventorySnapshot)
        if len(rows) == 2 and rows[0].snapshot_at == rows[1].snapshot_at:
            raise AmbiguousSourceDataError("Multiple latest inventory snapshots; specify import_batch_ids")
        return rows[0] if rows else None

    def list_stockout_periods(
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[StockoutPeriod]:
        start, end = time_range(start, end)
        model = StockoutPeriodModel
        query = select(model).where(
            model.started_at < end, or_(model.ended_at.is_(None), model.ended_at > start),
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if product_id is not None:
            query = query.where(model.product_id == product_id)
        if warehouse_id is not None:
            query = query.where(model.warehouse_id == warehouse_id)
        return self._read(query.order_by(model.started_at, model.id), StockoutPeriod)

    def list_active_in_transit(
        self, *, product_id: UUID | None = None, warehouse_id: UUID | None = None,
        expected_from: datetime | None = None, expected_before: datetime | None = None,
        include_undated: bool = False, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[InTransitItem]:
        lower = utc(expected_from) if expected_from is not None else None
        upper = utc(expected_before) if expected_before is not None else None
        if lower is not None and upper is not None and upper <= lower:
            raise ValueError("expected_before must be later than expected_from")
        model = InTransitItemModel
        dated = [model.expected_at.is_not(None)]
        if lower is not None:
            dated.append(model.expected_at >= lower)
        if upper is not None:
            dated.append(model.expected_at < upper)
        date_filter = and_(*dated)
        if include_undated:
            date_filter = or_(date_filter, model.expected_at.is_(None))
        query = select(model).where(
            model.status.in_((TransitStatus.PLANNED, TransitStatus.IN_TRANSIT)),
            date_filter, visible_import(model.import_batch_id, import_batch_ids),
        )
        if product_id is not None:
            query = query.where(model.product_id == product_id)
        if warehouse_id is not None:
            query = query.where(model.destination_warehouse_id == warehouse_id)
        return self._read(query.order_by(model.expected_at.asc().nulls_last(), model.id), InTransitItem)
