import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus
from backend.domain.entities.order_export import OrderExport
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.repositories.order_repository import (
    DuplicateOrderNumberError,
    InvalidOrderPersistenceStateError,
    OrderNotFoundError,
    RecommendationAlreadyOrderedError,
)
from backend.infrastructure.persistence.models.base import Base
from backend.infrastructure.persistence.models.orders import (
    OrderExportModel,
    PurchaseOrderItemModel,
    PurchaseOrderModel,
)
from backend.infrastructure.persistence.order_repository import SqlAlchemyOrderRepository


class OrderRepositoryTests(unittest.TestCase):
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
                PurchaseOrderModel.__table__,
                PurchaseOrderItemModel.__table__,
                OrderExportModel.__table__,
            ],
        )
        self.sessions = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.user_id = uuid4()
        self.supplier_id = uuid4()
        self.warehouse_id = uuid4()
        self.run_id = uuid4()
        self.product_id = uuid4()
        self.now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)

    @staticmethod
    def repository(session: Session) -> SqlAlchemyOrderRepository:
        return SqlAlchemyOrderRepository(session)

    def order(
        self,
        *,
        number: str = "PO-2026-0001",
        recommendation_id=None,
    ) -> PurchaseOrder:
        order = PurchaseOrder(
            order_number=number,
            supplier_id=self.supplier_id,
            warehouse_id=self.warehouse_id,
            created_from_run_id=self.run_id,
            created_by=self.user_id,
            created_at=self.now,
        )
        order.add_item(
            PurchaseOrderItem(
                recommendation_id=recommendation_id or uuid4(),
                product_id=self.product_id,
                recommended_quantity=Decimal("12"),
                approved_quantity=Decimal("10"),
                unit_price=Decimal("2.50"),
                total_amount=Decimal("25"),
            )
        )
        return order

    def test_add_and_get_order_with_snapshot_items(self):
        order = self.order()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            created = repository.add(order)
            loaded = repository.get_by_number(order.order_number)

        self.assertIsInstance(created, PurchaseOrder)
        self.assertEqual(loaded.id, order.id)
        self.assertEqual(loaded.items, order.items)
        self.assertEqual(loaded.status, PurchaseOrderStatus.DRAFT)

    def test_order_must_first_be_persisted_as_draft(self):
        order = self.order()
        order.approve(approved_by=self.user_id, approved_at=self.now + timedelta(minutes=1))
        with self.sessions() as session:
            with self.assertRaisesRegex(
                InvalidOrderPersistenceStateError, "persisted as draft"
            ):
                self.repository(session).add(order)

    def test_approve_save_and_export_are_audited(self):
        order = self.order()
        approved_at = self.now + timedelta(minutes=1)
        exported_at = approved_at + timedelta(minutes=1)
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add(order)
            order.approve(approved_by=self.user_id, approved_at=approved_at)
            approved = repository.save(order)
            export = OrderExport(
                purchase_order_id=order.id,
                format=ExportFormat.XLSX,
                file_name="order.xlsx",
                file_checksum="a" * 64,
                created_by=self.user_id,
                created_at=exported_at,
            )
            saved_export = repository.add_export(export)
            exported = repository.get(order.id)

        self.assertEqual(approved.status, PurchaseOrderStatus.APPROVED)
        self.assertEqual(saved_export, export)
        self.assertEqual(exported.status, PurchaseOrderStatus.EXPORTED)
        self.assertEqual(exported.exported_at, exported_at)

    def test_export_before_approval_is_rejected(self):
        order = self.order()
        export = OrderExport(
            purchase_order_id=order.id,
            format=ExportFormat.CSV,
            file_name="order.csv",
            file_checksum="b" * 64,
            created_by=self.user_id,
            created_at=self.now,
        )
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add(order)
            with self.assertRaisesRegex(
                InvalidOrderPersistenceStateError, "approved"
            ):
                repository.add_export(export)

    def test_duplicate_order_number_and_recommendation_are_domain_errors(self):
        recommendation_id = uuid4()
        first = self.order(number="PO-1", recommendation_id=recommendation_id)
        duplicate_number = self.order(number="PO-1")
        duplicate_recommendation = self.order(
            number="PO-2", recommendation_id=recommendation_id
        )
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add(first)
            with self.assertRaises(DuplicateOrderNumberError):
                repository.add(duplicate_number)
            with self.assertRaises(RecommendationAlreadyOrderedError):
                repository.add(duplicate_recommendation)

    def test_persisted_item_snapshots_cannot_be_changed(self):
        order = self.order()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add(order)
            order.items[0] = PurchaseOrderItem(
                id=order.items[0].id,
                recommendation_id=order.items[0].recommendation_id,
                product_id=order.items[0].product_id,
                recommended_quantity=order.items[0].recommended_quantity,
                approved_quantity=Decimal("99"),
            )
            with self.assertRaisesRegex(
                InvalidOrderPersistenceStateError, "items are immutable"
            ):
                repository.save(order)

    def test_list_and_missing_order(self):
        draft = self.order(number="PO-DRAFT")
        approved = self.order(number="PO-APPROVED")
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.add(draft)
            repository.add(approved)
            approved.approve(
                approved_by=self.user_id,
                approved_at=self.now + timedelta(minutes=1),
            )
            repository.save(approved)
            loaded = repository.list_by_supplier(
                self.supplier_id, status=PurchaseOrderStatus.APPROVED
            )
            with self.assertRaises(OrderNotFoundError):
                repository.list_exports(uuid4())

        self.assertEqual([item.id for item in loaded], [approved.id])

    def test_repository_does_not_commit(self):
        order = self.order()
        session = self.sessions()
        try:
            self.repository(session).add(order)
            session.rollback()
        finally:
            session.close()

        with self.sessions() as session:
            self.assertIsNone(self.repository(session).get(order.id))


if __name__ == "__main__":
    unittest.main()
