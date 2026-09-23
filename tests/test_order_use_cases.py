"""Application transactions against isolated SQLite with FK checks and real adapters."""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from openpyxl import load_workbook
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.application.use_cases.adjust_recommendation import AdjustRecommendation
from backend.application.use_cases.approve_order import ApproveOrder
from backend.application.use_cases.create_orders import CreateOrders
from backend.application.use_cases.export_order import ExportOrder
from backend.domain.entities.enums import CalculationRunStatus, PurchaseOrderStatus, RecommendationStatus, Urgency
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.enums import UserRole
from backend.domain.repositories.order_repository import OrderConflictError
from backend.domain.repositories.recommendation_repository import RecommendationConflictError, RecommendationNotFoundError
from backend.infrastructure.excel.exporter import XlsxOrderExporter
from backend.infrastructure.persistence.models import (
    Base, CalculationRunModel, OrderExportModel, ProductModel, PurchaseOrderItemModel,
    PurchaseOrderModel, RecommendationAdjustmentModel, RecommendationModel, SupplierModel,
    UserModel, WarehouseModel,
)
from backend.infrastructure.persistence.order_repository import SqlAlchemyOrderRepository
from backend.infrastructure.persistence.product_repository import SqlAlchemyProductRepository
from backend.infrastructure.persistence.recommendation_repository import SqlAlchemyRecommendationRepository
from backend.infrastructure.persistence.supplier_repository import SqlAlchemySupplierRepository
from backend.infrastructure.persistence.unit_of_work import RepositoryFactories, SqlAlchemyUnitOfWork
from backend.infrastructure.persistence.warehouse_repository import SqlAlchemyWarehouseRepository


D = Decimal


class OrderUseCaseTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = create_engine(f"sqlite+pysqlite:///{Path(directory.name) / 'orders.db'}")
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        unused = lambda session: None
        self.factories = RepositoryFactories(
            imports=unused, sales=unused, inventory=unused, calculation_runs=unused,
            recommendations=SqlAlchemyRecommendationRepository, orders=SqlAlchemyOrderRepository,
            products=SqlAlchemyProductRepository, suppliers=SqlAlchemySupplierRepository,
            warehouses=SqlAlchemyWarehouseRepository,
        )
        self.user, self.other_user, self.run = uuid4(), uuid4(), uuid4()
        self.product, self.supplier, self.warehouse = uuid4(), uuid4(), uuid4()
        self.other_supplier, self.other_warehouse = uuid4(), uuid4()
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with self.sessions.begin() as session:
            for actor in (self.user, self.other_user):
                session.execute(UserModel.__table__.insert().values(
                    id=actor, external_id=str(actor), display_name="Buyer", role=UserRole.BUYER))
            for supplier in (self.supplier, self.other_supplier):
                session.execute(SupplierModel.__table__.insert().values(id=supplier, code=str(supplier), name="Supplier"))
            for warehouse in (self.warehouse, self.other_warehouse):
                session.execute(WarehouseModel.__table__.insert().values(id=warehouse, code=str(warehouse), name="Warehouse"))
            session.execute(ProductModel.__table__.insert().values(
                id=self.product, sku="=literal-sku", name="Product", unit="pcs"))
            session.execute(CalculationRunModel.__table__.insert().values(
                id=self.run, status=CalculationRunStatus.COMPLETED, started_by=self.user,
                forecast_horizon_days=30, source_cutoff_at=self.now, algorithm_version="test",
                parameters={}, started_at=self.now))
        self.adjust = AdjustRecommendation(self.uow)
        self.create = CreateOrders(self.uow)
        self.approve = ApproveOrder(self.uow)
        self.exporter = XlsxOrderExporter()
        self.export = ExportOrder(self.uow, self.exporter)

    def uow(self):
        return SqlAlchemyUnitOfWork(self.sessions, self.factories)

    def recommendation(self, **overrides):
        values = dict(
            id=uuid4(), calculation_run_id=self.run, product_id=self.product,
            supplier_id=self.supplier, warehouse_id=self.warehouse,
            forecast_quantity=D(20), current_stock=D(0), in_transit_quantity=D(0),
            material_requirement_quantity=D(0), safety_stock=D(0), shortage_quantity=D(20),
            quantity_before_rounding=D(20), moq=D(10), package_size=D(5), recommended_quantity=D(20),
            effective_quantity=D(15), risk_score=D("0.5"), urgency=Urgency.MEDIUM,
            status=RecommendationStatus.ACCEPTED, explanation="Synthetic", calculation_details={},
            version=1, created_at=self.now, updated_at=self.now,
        )
        values.update(overrides)
        with self.sessions.begin() as session:
            session.execute(RecommendationModel.__table__.insert().values(**values))
        return values["id"]

    def count(self, model):
        with self.sessions() as session:
            return session.scalar(select(func.count()).select_from(model))

    def load_recommendation(self, rec_id):
        with self.uow() as uow:
            return uow.recommendations.get(rec_id)

    def load_order(self, order_id):
        with self.uow() as uow:
            return uow.orders.get(order_id)

    def draft(self):
        self.recommendation()
        return self.create.execute(self.run, user_id=self.user)[0]

    def approved(self):
        return self.approve.execute(self.draft().id, user_id=self.user)

    def test_adjustment_history_and_original_calculation_are_preserved(self):
        rec = self.recommendation()
        first = self.adjust.execute(rec, expected_version=1, new_quantity=D(7), reason="Manual override", user_id=self.user)
        second = self.adjust.execute(rec, expected_version=2, new_quantity=D(0), reason="Cancel need", user_id=self.other_user)
        with self.uow() as uow:
            history = uow.recommendations.list_adjustments(rec)
        self.assertEqual((first.status, second.status), (RecommendationStatus.ADJUSTED,) * 2)
        self.assertEqual(second.version, 3)
        self.assertEqual(second.recommended_quantity, D(20))
        self.assertEqual([(h.previous_quantity, h.new_quantity, h.changed_by) for h in history],
                         [(D(15), D(7), self.user), (D(7), D(0), self.other_user)])
        self.assertTrue(all(h.changed_at.tzinfo for h in history))
        self.assertEqual(self.create.execute(self.run, user_id=self.user), ())

    def test_version_conflict_and_missing_recommendation(self):
        rec = self.recommendation()
        with self.assertRaises(RecommendationConflictError):
            self.adjust.execute(rec, expected_version=2, new_quantity=D(5), reason="why", user_id=self.user)
        with self.assertRaises(RecommendationNotFoundError):
            self.adjust.execute(uuid4(), expected_version=1, new_quantity=D(5), reason="why", user_id=self.user)
        self.assertEqual(self.count(RecommendationAdjustmentModel), 0)

    def test_closed_recommendations_cannot_be_adjusted(self):
        rec = self.recommendation()
        for status in (RecommendationStatus.REJECTED, RecommendationStatus.CONVERTED_TO_ORDER):
            with self.sessions.begin() as session:
                session.execute(update(RecommendationModel).where(RecommendationModel.id == rec).values(status=status))
            with self.assertRaisesRegex(ValueError, "closed"):
                self.adjust.execute(rec, expected_version=1, new_quantity=D(5), reason="why", user_id=self.user)
        self.assertEqual(self.count(RecommendationAdjustmentModel), 0)

    def test_reason_and_quantity_validation(self):
        rec = self.recommendation()
        for reason in ("", " \n\t", None, "x" * 2001):
            with self.subTest(reason=str(reason)[:10]), self.assertRaises(ValueError):
                self.adjust.execute(rec, expected_version=1, new_quantity=D(5), reason=reason, user_id=self.user)
        for quantity in (D(-1), D("NaN"), D("Infinity"), D("0.00001"), D("100000000000000"), 1.5):
            with self.subTest(quantity=quantity), self.assertRaises((ValueError, TypeError)):
                self.adjust.execute(rec, expected_version=1, new_quantity=quantity, reason="why", user_id=self.user)
        self.assertEqual(self.load_recommendation(rec).version, 1)

    def test_stale_writer_loses_sql_compare_and_swap(self):
        rec = self.recommendation()
        with self.sessions() as first, self.sessions() as second:
            a, b = SqlAlchemyRecommendationRepository(first), SqlAlchemyRecommendationRepository(second)
            left, right = a.get(rec), b.get(rec)
            left_adjustment = left.adjust(D(10), reason="first", changed_by=self.user)
            right_adjustment = right.adjust(D(5), reason="second", changed_by=self.other_user)
            a.save_adjustment(left, left_adjustment, expected_version=1)
            first.commit()
            with self.assertRaises(RecommendationConflictError):
                b.save_adjustment(right, right_adjustment, expected_version=1)
            second.rollback()
        self.assertEqual(self.load_recommendation(rec).effective_quantity, D(10))
        self.assertEqual(self.count(RecommendationAdjustmentModel), 1)

    def test_failed_audit_insert_rolls_back_quantity_and_version(self):
        rec = self.recommendation()
        with self.assertRaises(IntegrityError):
            self.adjust.execute(rec, expected_version=1, new_quantity=D(5), reason="why", user_id=uuid4())
        stored = self.load_recommendation(rec)
        self.assertEqual((stored.effective_quantity, stored.version), (D(15), 1))
        self.assertEqual(self.count(RecommendationAdjustmentModel), 0)

    def test_create_groups_by_supplier_and_warehouse_and_snapshots_quantities(self):
        for supplier, warehouse in ((self.supplier, self.warehouse), (self.supplier, self.other_warehouse),
                                    (self.other_supplier, self.warehouse)):
            self.recommendation(supplier_id=supplier, warehouse_id=warehouse)
        orders = self.create.execute(self.run, user_id=self.user)
        self.assertEqual(len(orders), 3)
        self.assertEqual(len({(o.supplier_id, o.warehouse_id) for o in orders}), 3)
        for order in orders:
            self.assertEqual(order.status, PurchaseOrderStatus.DRAFT)
            self.assertIsNone(order.approved_at)
            self.assertEqual((order.items[0].recommended_quantity, order.items[0].approved_quantity), (D(20), D(15)))
            rec = self.load_recommendation(order.items[0].recommendation_id)
            self.assertEqual((rec.status, rec.version), (RecommendationStatus.CONVERTED_TO_ORDER, 2))
        self.assertEqual(self.create.execute(self.run, user_id=self.user), ())
        with self.sessions.begin() as session:
            session.execute(update(RecommendationModel).values(effective_quantity=D(99)))
        self.assertEqual(self.load_order(orders[0].id).items[0].approved_quantity, D(15))

    def test_create_excludes_zero_unaccepted_and_previously_ordered(self):
        accepted = self.recommendation()
        self.recommendation(supplier_id=self.other_supplier, effective_quantity=D(0))
        self.recommendation(warehouse_id=self.other_warehouse, status=RecommendationStatus.SUGGESTED)
        existing = PurchaseOrder(order_number="legacy", supplier_id=self.supplier, warehouse_id=self.warehouse,
                                 created_from_run_id=self.run, created_by=self.user)
        existing.add_item(PurchaseOrderItem(recommendation_id=accepted, product_id=self.product,
                                            recommended_quantity=D(20), approved_quantity=D(15)))
        with self.uow() as uow:
            uow.orders.add(existing)
            uow.commit()
        self.assertEqual(self.create.execute(self.run, user_id=self.user), ())
        self.assertEqual(self.count(PurchaseOrderModel), 1)
        # Defensive guard also handles legacy rows whose recommendation status was not updated.
        with self.assertRaises(RecommendationConflictError):
            self.adjust.execute(accepted, expected_version=1, new_quantity=D(5), reason="why", user_id=self.user)

    def test_creation_failure_rolls_back_all_groups_and_claims(self):
        recs = [self.recommendation(), self.recommendation(supplier_id=self.other_supplier)]
        original = SqlAlchemyOrderRepository.add
        calls = []

        def fail_second(repo, order):
            result = original(repo, order)
            calls.append(order.id)
            if len(calls) == 2:
                raise RuntimeError("order insert failed")
            return result

        with patch.object(SqlAlchemyOrderRepository, "add", fail_second), self.assertRaises(RuntimeError):
            self.create.execute(self.run, user_id=self.user)
        self.assertEqual(self.count(PurchaseOrderModel), 0)
        self.assertEqual(self.count(PurchaseOrderItemModel), 0)
        self.assertTrue(all(self.load_recommendation(r).status is RecommendationStatus.ACCEPTED for r in recs))

    def test_stale_creation_cannot_duplicate_an_order(self):
        rec = self.recommendation()
        stale = self.load_recommendation(rec)
        self.create.execute(self.run, user_id=self.user)
        with patch.object(SqlAlchemyRecommendationRepository, "list_orderable", return_value=(stale,)):
            with self.assertRaises(RecommendationConflictError):
                self.create.execute(self.run, user_id=self.other_user)
        self.assertEqual(self.count(PurchaseOrderModel), 1)
        self.assertEqual(self.count(PurchaseOrderItemModel), 1)

    def test_approval_records_actor_and_repeated_call_does_not_overwrite(self):
        order = self.approved()
        with self.assertRaisesRegex(ValueError, "draft"):
            self.approve.execute(order.id, user_id=self.other_user)
        stored = self.load_order(order.id)
        self.assertEqual((stored.status, stored.approved_by, stored.approved_at),
                         (PurchaseOrderStatus.APPROVED, self.user, order.approved_at))

    def test_empty_and_cancelled_orders_cannot_be_approved(self):
        order = PurchaseOrder(order_number="empty", supplier_id=self.supplier, warehouse_id=self.warehouse,
                              created_from_run_id=self.run, created_by=self.user)
        with self.uow() as uow:
            uow.orders.add(order)
            uow.commit()
        with self.assertRaisesRegex(ValueError, "empty"):
            self.approve.execute(order.id, user_id=self.user)
        with self.sessions.begin() as session:
            session.execute(update(PurchaseOrderModel).where(PurchaseOrderModel.id == order.id).values(status=PurchaseOrderStatus.CANCELLED))
        with self.assertRaisesRegex(ValueError, "draft"):
            self.approve.execute(order.id, user_id=self.user)

    def test_stale_approval_cannot_overwrite_winner(self):
        draft = self.draft()
        stale = self.load_order(draft.id)
        winner = self.approve.execute(draft.id, user_id=self.user)
        stale.approve(approved_by=self.other_user)
        with self.uow() as uow, self.assertRaises(OrderConflictError):
            uow.orders.save(stale, expected_status=PurchaseOrderStatus.DRAFT)
        self.assertEqual(self.load_order(draft.id).approved_at, winner.approved_at)

    def test_export_requires_approval(self):
        order = self.draft()
        with patch.object(self.exporter, "render") as render, self.assertRaisesRegex(ValueError, "approved"):
            self.export.execute(order.id, user_id=self.user)
        render.assert_not_called()
        self.assertEqual(self.count(OrderExportModel), 0)

    def test_export_bytes_checksum_content_and_status(self):
        order = self.approved()
        result = self.export.execute(order.id, user_id=self.other_user)
        self.assertEqual(result.metadata.file_checksum, hashlib.sha256(result.content).hexdigest())
        self.assertEqual(result.metadata.created_by, self.other_user)
        workbook = load_workbook(BytesIO(result.content), data_only=False)
        try:
            sheet = workbook.active
            self.assertEqual(sheet["B3"].value, str(self.supplier))
            self.assertEqual(sheet["B5"].value, str(self.warehouse))
            self.assertEqual(sheet["A10"].value, "=literal-sku")
            self.assertEqual(sheet["A10"].data_type, "s")
            self.assertEqual(sheet["D10"].value, "20.0000")
            self.assertEqual(sheet["E10"].value, "15.0000")
        finally:
            workbook.close()
        stored = self.load_order(order.id)
        self.assertEqual(stored.status, PurchaseOrderStatus.EXPORTED)
        self.assertEqual(stored.exported_at, result.metadata.created_at)
        with self.uow() as uow:
            self.assertEqual(uow.orders.list_exports(order.id), (result.metadata,))
        with self.assertRaisesRegex(ValueError, "approved"):
            self.export.execute(order.id, user_id=self.user)
        self.assertEqual(self.count(OrderExportModel), 1)

    def test_workbook_write_failure_leaves_order_approved(self):
        order = self.approved()
        with patch("backend.infrastructure.excel.exporter.Workbook.save", side_effect=OSError("stream failed")):
            with self.assertRaises(OSError):
                self.export.execute(order.id, user_id=self.user)
        self.assertEqual(self.load_order(order.id).status, PurchaseOrderStatus.APPROVED)
        self.assertEqual(self.count(OrderExportModel), 0)

    def test_metadata_failure_rolls_back_export_transition(self):
        order = self.approved()
        original = SqlAlchemyOrderRepository.add_export

        def fail_after_write(repo, metadata):
            original(repo, metadata)
            raise RuntimeError("metadata storage failed")

        with patch.object(SqlAlchemyOrderRepository, "add_export", fail_after_write):
            with self.assertRaises(RuntimeError):
                self.export.execute(order.id, user_id=self.user)
        self.assertEqual(self.load_order(order.id).status, PurchaseOrderStatus.APPROVED)
        self.assertIsNone(self.load_order(order.id).exported_at)
        self.assertEqual(self.count(OrderExportModel), 0)

    def test_commit_failure_rolls_back_export_and_returns_no_file(self):
        order = self.approved()
        with patch.object(Session, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaises(RuntimeError):
                self.export.execute(order.id, user_id=self.user)
        self.assertEqual(self.load_order(order.id).status, PurchaseOrderStatus.APPROVED)
        self.assertEqual(self.count(OrderExportModel), 0)

    def test_concurrent_status_change_is_detected_by_sql_update(self):
        order = self.draft()
        with self.sessions() as session:
            repo = SqlAlchemyOrderRepository(session)
            candidate = repo.get(order.id)
            candidate.approve(approved_by=self.user)
            original = repo._change_status

            def competing_write(order_id, expected_status, **values):
                # Interleave a winner after the repository's checks but before its UPDATE.
                session.execute(update(PurchaseOrderModel).where(PurchaseOrderModel.id == order_id)
                                .values(status=PurchaseOrderStatus.CANCELLED))
                original(order_id, expected_status, **values)

            with patch.object(repo, "_change_status", competing_write), self.assertRaises(OrderConflictError):
                repo.save(candidate, expected_status=PurchaseOrderStatus.DRAFT)
            session.rollback()

    def test_postgresql_cas_statements_include_guards(self):
        rec = self.recommendation()
        statements = []

        def capture(state):
            if state.is_update:
                statements.append(str(state.statement.compile(dialect=postgresql.dialect())))

        event.listen(Session, "do_orm_execute", capture)
        try:
            self.adjust.execute(rec, expected_version=1, new_quantity=D(10), reason="why", user_id=self.user)
        finally:
            event.remove(Session, "do_orm_execute", capture)
        self.assertEqual(len(statements), 1)
        where = statements[0].split("WHERE", 1)[1]
        self.assertIn("recommendations.version =", where)
        self.assertIn("recommendations.status IN", where)
        self.assertIn("NOT (EXISTS", where)

    def test_suggested_can_be_adjusted_but_requires_acceptance_before_ordering(self):
        rec = self.recommendation(status=RecommendationStatus.SUGGESTED)
        result = self.adjust.execute(rec, expected_version=1, new_quantity=D("12.5000"),
                                     reason="Forecast override", user_id=self.user)
        self.assertEqual(result.status, RecommendationStatus.ADJUSTED)
        self.assertEqual(self.create.execute(self.run, user_id=self.user), ())

    def test_multiple_products_in_one_group_share_a_draft(self):
        self.recommendation()
        second_product = uuid4()
        with self.sessions.begin() as session:
            session.execute(ProductModel.__table__.insert().values(
                id=second_product, sku="second", name="Second", unit="pcs"))
        self.recommendation(product_id=second_product)
        orders = self.create.execute(self.run, user_id=self.user)
        self.assertEqual(len(orders), 1)
        self.assertEqual(len(orders[0].items), 2)

    def test_export_loses_to_concurrent_export_without_duplicate_audit(self):
        order = self.approved()
        # Keep the losing reader's approved snapshot while another complete use case wins.
        with self.sessions() as session:
            repository = SqlAlchemyOrderRepository(session)
            snapshot = session.get(PurchaseOrderModel, order.id)
            self.assertEqual(snapshot.status, PurchaseOrderStatus.APPROVED)
            winner = self.export.execute(order.id, user_id=self.user)
            with self.assertRaises(OrderConflictError):
                repository.add_export(replace(winner.metadata, id=uuid4(), created_by=self.other_user))
            session.rollback()
        self.assertEqual(self.count(OrderExportModel), 1)
        with self.uow() as uow:
            self.assertEqual(uow.orders.list_exports(order.id), (winner.metadata,))

    def test_domain_and_application_import_without_infrastructure(self):
        script = (
            "from backend.domain.value_objects.quantity import validate_quantity; "
            "from backend.application.use_cases.export_order import ExportOrder; "
            "from backend.application.use_cases.create_orders import CreateOrders; import sys; "
            "assert not any(k.startswith(('sqlalchemy', 'openpyxl', 'backend.infrastructure')) for k in sys.modules)"
        )
        result = subprocess.run([sys.executable, "-B", "-S", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
