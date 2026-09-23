from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.domain.entities.imports import (
    InventorySnapshot,
    InTransitItem,
    StockoutPeriod,
)
from backend.domain.enums import TransitStatus
from backend.infrastructure.persistence.models.imports import (
    InventorySnapshotModel,
    InTransitItemModel,
    StockoutPeriodModel,
)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must contain timezone information")


class SqlAlchemyInventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_snapshots(
        self, snapshots: Iterable[InventorySnapshot]
    ) -> Sequence[InventorySnapshot]:
        entities = tuple(snapshots)
        self._session.add_all(
            InventorySnapshotModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                snapshot_at=item.snapshot_at,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                quantity_available=item.quantity_available,
            )
            for item in entities
        )
        self._session.flush()
        return entities

    def get_latest_snapshot(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        as_of: datetime,
    ) -> InventorySnapshot | None:
        _require_aware(as_of, "as_of")
        model = self._session.scalar(
            select(InventorySnapshotModel)
            .where(
                InventorySnapshotModel.product_id == product_id,
                InventorySnapshotModel.warehouse_id == warehouse_id,
                InventorySnapshotModel.snapshot_at <= as_of,
            )
            .order_by(InventorySnapshotModel.snapshot_at.desc())
            .limit(1)
        )
        return self._snapshot_to_domain(model) if model is not None else None

    def list_snapshots(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        started_at: datetime,
        ended_at: datetime,
    ) -> Sequence[InventorySnapshot]:
        self._validate_period(started_at, ended_at)
        models = self._session.scalars(
            select(InventorySnapshotModel)
            .where(
                InventorySnapshotModel.product_id == product_id,
                InventorySnapshotModel.warehouse_id == warehouse_id,
                InventorySnapshotModel.snapshot_at >= started_at,
                InventorySnapshotModel.snapshot_at <= ended_at,
            )
            .order_by(InventorySnapshotModel.snapshot_at)
        ).all()
        return tuple(self._snapshot_to_domain(model) for model in models)

    def add_stockout_periods(
        self, periods: Iterable[StockoutPeriod]
    ) -> Sequence[StockoutPeriod]:
        entities = tuple(periods)
        self._session.add_all(
            StockoutPeriodModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                started_at=item.started_at,
                ended_at=item.ended_at,
                source=item.source,
                confidence=item.confidence,
            )
            for item in entities
        )
        self._session.flush()
        return entities

    def list_stockout_periods(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        started_at: datetime,
        ended_at: datetime,
    ) -> Sequence[StockoutPeriod]:
        self._validate_period(started_at, ended_at)
        models = self._session.scalars(
            select(StockoutPeriodModel)
            .where(
                StockoutPeriodModel.product_id == product_id,
                StockoutPeriodModel.warehouse_id == warehouse_id,
                StockoutPeriodModel.started_at <= ended_at,
                or_(
                    StockoutPeriodModel.ended_at.is_(None),
                    StockoutPeriodModel.ended_at >= started_at,
                ),
            )
            .order_by(StockoutPeriodModel.started_at)
        ).all()
        return tuple(self._stockout_to_domain(model) for model in models)

    def add_in_transit_items(
        self, items: Iterable[InTransitItem]
    ) -> Sequence[InTransitItem]:
        entities = tuple(items)
        self._session.add_all(
            InTransitItemModel(
                id=item.id,
                import_batch_id=item.import_batch_id,
                external_order_number=item.external_order_number,
                supplier_id=item.supplier_id,
                product_id=item.product_id,
                destination_warehouse_id=item.destination_warehouse_id,
                quantity=item.quantity,
                expected_at=item.expected_at,
                status=item.status,
            )
            for item in entities
        )
        self._session.flush()
        return entities

    def list_open_in_transit(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        *,
        expected_by: datetime | None = None,
    ) -> Sequence[InTransitItem]:
        conditions = [
            InTransitItemModel.product_id == product_id,
            InTransitItemModel.destination_warehouse_id == warehouse_id,
            InTransitItemModel.status.in_(
                (TransitStatus.PLANNED, TransitStatus.IN_TRANSIT)
            ),
        ]
        if expected_by is not None:
            _require_aware(expected_by, "expected_by")
            conditions.append(
                or_(
                    InTransitItemModel.expected_at.is_(None),
                    InTransitItemModel.expected_at <= expected_by,
                )
            )
        models = self._session.scalars(
            select(InTransitItemModel)
            .where(*conditions)
            .order_by(
                InTransitItemModel.expected_at.is_(None),
                InTransitItemModel.expected_at,
                InTransitItemModel.id,
            )
        ).all()
        return tuple(self._transit_to_domain(model) for model in models)

    @staticmethod
    def _validate_period(started_at: datetime, ended_at: datetime) -> None:
        _require_aware(started_at, "started_at")
        _require_aware(ended_at, "ended_at")
        if ended_at < started_at:
            raise ValueError("ended_at must be >= started_at")

    @staticmethod
    def _snapshot_to_domain(model: InventorySnapshotModel) -> InventorySnapshot:
        return InventorySnapshot(
            id=model.id,
            import_batch_id=model.import_batch_id,
            product_id=model.product_id,
            warehouse_id=model.warehouse_id,
            snapshot_at=_aware(model.snapshot_at),
            quantity_on_hand=model.quantity_on_hand,
            quantity_reserved=model.quantity_reserved,
            quantity_available=model.quantity_available,
        )

    @staticmethod
    def _stockout_to_domain(model: StockoutPeriodModel) -> StockoutPeriod:
        return StockoutPeriod(
            id=model.id,
            import_batch_id=model.import_batch_id,
            product_id=model.product_id,
            warehouse_id=model.warehouse_id,
            started_at=_aware(model.started_at),
            ended_at=_aware(model.ended_at) if model.ended_at is not None else None,
            source=model.source,
            confidence=model.confidence,
        )

    @staticmethod
    def _transit_to_domain(model: InTransitItemModel) -> InTransitItem:
        return InTransitItem(
            id=model.id,
            import_batch_id=model.import_batch_id,
            external_order_number=model.external_order_number,
            supplier_id=model.supplier_id,
            product_id=model.product_id,
            destination_warehouse_id=model.destination_warehouse_id,
            quantity=model.quantity,
            expected_at=_aware(model.expected_at) if model.expected_at is not None else None,
            status=model.status,
        )
