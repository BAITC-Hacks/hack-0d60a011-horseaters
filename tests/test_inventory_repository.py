import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.entities.imports import (
    InventorySnapshot,
    InTransitItem,
    StockoutPeriod,
)
from backend.domain.enums import ImportSourceType, ImportStatus, StockoutSource, TransitStatus, UserRole
from backend.infrastructure.persistence.inventory_repository import (
    SqlAlchemyInventoryRepository,
)
from backend.infrastructure.persistence.models.base import Base
from backend.infrastructure.persistence.models.imports import (
    ImportBatchModel,
    InventorySnapshotModel,
    InTransitItemModel,
    StockoutPeriodModel,
)
from backend.infrastructure.persistence.models.catalog import UserModel


class InventoryRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(
            self.engine,
            tables=[
                UserModel.__table__,
                ImportBatchModel.__table__,
                InventorySnapshotModel.__table__,
                StockoutPeriodModel.__table__,
                InTransitItemModel.__table__,
            ],
        )
        self.sessions = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.import_batch_id = uuid4()
        self.product_id = uuid4()
        self.warehouse_id = uuid4()
        self.supplier_id = uuid4()
        self.now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
        # Calculation reads require a completed import, not an orphan batch UUID.
        with self.sessions.begin() as session:
            user_id = uuid4()
            session.add(UserModel(id=user_id, external_id="inventory-test", display_name="Test",
                                  role=UserRole.BUYER, created_at=self.now))
            session.flush()
            session.add(ImportBatchModel(
                id=self.import_batch_id, source_type=ImportSourceType.INVENTORY,
                status=ImportStatus.COMPLETED, file_name="synthetic.xlsx", file_checksum="a" * 64,
                imported_by=user_id, imported_at=self.now,
            ))

    @staticmethod
    def repository(session: Session) -> SqlAlchemyInventoryRepository:
        return SqlAlchemyInventoryRepository(session)

    def snapshot(self, *, at: datetime, available: str) -> InventorySnapshot:
        quantity = Decimal(available)
        return InventorySnapshot(
            import_batch_id=self.import_batch_id,
            product_id=self.product_id,
            warehouse_id=self.warehouse_id,
            snapshot_at=at,
            quantity_on_hand=quantity,
            quantity_reserved=Decimal("0"),
            quantity_available=quantity,
        )

    def transit(
        self,
        *,
        status: TransitStatus,
        expected_at: datetime | None,
    ) -> InTransitItem:
        return InTransitItem(
            import_batch_id=self.import_batch_id,
            supplier_id=self.supplier_id,
            product_id=self.product_id,
            destination_warehouse_id=self.warehouse_id,
            quantity=Decimal("10"),
            status=status,
            expected_at=expected_at,
        )

    def test_latest_snapshot_respects_cutoff_and_returns_domain_entity(self):
        older = self.snapshot(at=self.now - timedelta(days=2), available="5")
        current = self.snapshot(at=self.now, available="8")
        future = self.snapshot(at=self.now + timedelta(days=2), available="13")
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add_snapshots([future, older, current])
            loaded = repository.get_latest_snapshot(
                self.product_id, self.warehouse_id, as_of=self.now
            )

        self.assertIsInstance(loaded, InventorySnapshot)
        self.assertEqual(loaded.id, current.id)
        self.assertEqual(loaded.quantity_available, Decimal("8.0000"))

    def test_snapshot_range_is_inclusive_and_chronological(self):
        snapshots = [
            self.snapshot(at=self.now + timedelta(days=offset), available=str(offset + 5))
            for offset in (-2, 0, 2)
        ]
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add_snapshots(snapshots)
            loaded = repository.list_snapshots(
                self.product_id,
                self.warehouse_id,
                started_at=self.now - timedelta(days=1),
                ended_at=self.now + timedelta(days=2),
            )

        self.assertEqual([item.id for item in loaded], [snapshots[1].id, snapshots[2].id])

    def test_stockout_query_returns_overlapping_and_open_periods(self):
        overlapping = StockoutPeriod(
            product_id=self.product_id,
            warehouse_id=self.warehouse_id,
            started_at=self.now - timedelta(days=3),
            ended_at=self.now - timedelta(hours=1),
            source=StockoutSource.IMPORTED,
        )
        open_period = StockoutPeriod(
            product_id=self.product_id,
            warehouse_id=self.warehouse_id,
            started_at=self.now + timedelta(hours=1),
            source=StockoutSource.INFERRED,
            confidence=Decimal("0.8"),
        )
        outside = StockoutPeriod(
            product_id=self.product_id,
            warehouse_id=self.warehouse_id,
            started_at=self.now - timedelta(days=10),
            ended_at=self.now - timedelta(days=9),
            source=StockoutSource.IMPORTED,
        )
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add_stockout_periods([outside, open_period, overlapping])
            loaded = repository.list_stockout_periods(
                self.product_id,
                self.warehouse_id,
                started_at=self.now - timedelta(days=1),
                ended_at=self.now + timedelta(days=1),
            )

        self.assertEqual([item.id for item in loaded], [overlapping.id, open_period.id])

    def test_open_transit_excludes_closed_and_items_after_horizon(self):
        planned = self.transit(
            status=TransitStatus.PLANNED,
            expected_at=self.now + timedelta(days=2),
        )
        unknown_eta = self.transit(status=TransitStatus.IN_TRANSIT, expected_at=None)
        too_late = self.transit(
            status=TransitStatus.IN_TRANSIT,
            expected_at=self.now + timedelta(days=20),
        )
        received = self.transit(
            status=TransitStatus.RECEIVED,
            expected_at=self.now,
        )
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add_in_transit_items([too_late, received, unknown_eta, planned])
            loaded = repository.list_open_in_transit(
                self.product_id,
                self.warehouse_id,
                expected_by=self.now + timedelta(days=7),
            )

        self.assertEqual({item.id for item in loaded}, {planned.id, unknown_eta.id})

    def test_invalid_query_period_is_rejected(self):
        with self.sessions() as session:
            repository = self.repository(session)
            with self.assertRaisesRegex(ValueError, "ended_at"):
                repository.list_snapshots(
                    self.product_id,
                    self.warehouse_id,
                    started_at=self.now,
                    ended_at=self.now - timedelta(seconds=1),
                )

    def test_repository_does_not_commit(self):
        snapshot = self.snapshot(at=self.now, available="4")
        session = self.sessions()
        try:
            self.repository(session).add_snapshots([snapshot])
            session.rollback()
        finally:
            session.close()

        with self.sessions() as session:
            loaded = self.repository(session).get_latest_snapshot(
                self.product_id, self.warehouse_id, as_of=self.now
            )
        self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
