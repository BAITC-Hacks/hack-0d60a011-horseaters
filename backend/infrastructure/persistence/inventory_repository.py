from collections.abc import Collection, Iterable, Sequence
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
        self, start: datetime | UUID | None = None, end: datetime | UUID | None = None, *,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None, import_batch_ids: Collection[UUID] | None = None,
        started_at: datetime | None = None, ended_at: datetime | None = None,
    ) -> list[StockoutPeriod]:
        inclusive = started_at is not None or ended_at is not None
        if inclusive:
            if started_at is None or ended_at is None:
                raise TypeError("Both started_at and ended_at are required")
            if start is not None:
                if not isinstance(start, UUID):
                    raise TypeError("Do not mix start/end datetimes with started_at/ended_at")
                if product_id is not None:
                    raise TypeError("Specify product_id and warehouse_id only once")
                product_id = start
            if end is not None:
                if not isinstance(end, UUID):
                    raise TypeError("Do not mix start/end datetimes with started_at/ended_at")
                if warehouse_id is not None:
                    raise TypeError("Specify product_id and warehouse_id only once")
                warehouse_id = end
            if product_id is None or warehouse_id is None:
                raise TypeError("The started_at/ended_at API requires product_id and warehouse_id")
            start, end = utc(started_at), utc(ended_at)
            if end < start:
                raise ValueError("ended_at must be >= started_at")
        else:
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                raise TypeError("start and end must be datetimes")
            start, end = time_range(start, end)
        model = StockoutPeriodModel
        starts_before_end = model.started_at <= end if inclusive else model.started_at < end
        ends_after_start = model.ended_at >= start if inclusive else model.ended_at > start
        query = select(model).where(
            starts_before_end, or_(model.ended_at.is_(None), ends_after_start),
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

    def add_snapshots(
        self, snapshots: Iterable[InventorySnapshot]
    ) -> Sequence[InventorySnapshot]:
        entities = tuple(snapshots)
        self.session.add_all(
            InventorySnapshotModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                snapshot_at=utc(item.snapshot_at),
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                quantity_available=item.quantity_available,
            )
            for item in entities
        )
        self.session.flush()
        return entities

    def add_stockout_periods(
        self, periods: Iterable[StockoutPeriod]
    ) -> Sequence[StockoutPeriod]:
        entities = tuple(periods)
        self.session.add_all(
            StockoutPeriodModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                started_at=utc(item.started_at),
                ended_at=utc(item.ended_at) if item.ended_at is not None else None,
                source=item.source,
                confidence=item.confidence,
            )
            for item in entities
        )
        self.session.flush()
        return entities

    def add_in_transit_items(
        self, items: Iterable[InTransitItem]
    ) -> Sequence[InTransitItem]:
        entities = tuple(items)
        self.session.add_all(
            InTransitItemModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                external_order_number=item.external_order_number,
                supplier_id=item.supplier_id,
                product_id=item.product_id,
                destination_warehouse_id=item.destination_warehouse_id,
                quantity=item.quantity,
                expected_at=utc(item.expected_at) if item.expected_at is not None else None,
                status=item.status,
            )
            for item in entities
        )
        self.session.flush()
        return entities

    def list_snapshots(
        self, product_id: UUID, warehouse_id: UUID, *,
        started_at: datetime, ended_at: datetime,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> Sequence[InventorySnapshot]:
        """Existing inclusive range API, restricted to completed imports."""
        start, end = utc(started_at), utc(ended_at)
        if end < start:
            raise ValueError("ended_at must be >= started_at")
        model = InventorySnapshotModel
        query = select(model).where(
            model.product_id == product_id, model.warehouse_id == warehouse_id,
            model.snapshot_at >= start, model.snapshot_at <= end,
            visible_import(model.import_batch_id, import_batch_ids),
        ).order_by(model.snapshot_at, model.id)
        return tuple(self._read(query, InventorySnapshot))

    def list_open_in_transit(
        self, product_id: UUID, warehouse_id: UUID, *, expected_by: datetime | None = None,
    ) -> Sequence[InTransitItem]:
        """Existing inclusive ETA API; undated open items remain included."""
        model = InTransitItemModel
        query = select(model).where(
            model.product_id == product_id, model.destination_warehouse_id == warehouse_id,
            model.status.in_((TransitStatus.PLANNED, TransitStatus.IN_TRANSIT)),
            visible_import(model.import_batch_id, None),
        )
        if expected_by is not None:
            query = query.where(or_(model.expected_at.is_(None), model.expected_at <= utc(expected_by)))
        return tuple(self._read(query.order_by(model.expected_at.asc().nulls_last(), model.id), InTransitItem))
