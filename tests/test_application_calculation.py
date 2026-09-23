import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import create_engine, event

from backend.application.dto.calculation import RunCalculationCommand
from backend.application.use_cases.explain_recommendation import ExplainRecommendation
from backend.application.use_cases.get_calculation_run import GetCalculationRun
from backend.application.use_cases.list_recommendations import ListRecommendations, ListRecommendationsQuery
from backend.application.use_cases.run_calculation import RunCalculation
from backend.domain.entities.enums import CalculationRunStatus
from backend.domain.enums import ImportSourceType, ImportStatus, TransactionType, UserRole
from backend.infrastructure.persistence.database import create_session_factory
from backend.infrastructure.persistence.models import (
    Base, ImportBatchModel, ProductModel, SalesTransactionModel, SupplierModel,
    SupplierProductModel, UserModel, WarehouseModel,
)
from backend.infrastructure.persistence.application_uow import create_application_uow_factory
from backend.infrastructure.persistence.sales_repository import SqlAlchemySalesRepository
from backend.infrastructure.persistence.models import MonthlySalesModel
from backend.domain.value_objects.demand import DemandSource


class CalculationApplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = create_session_factory(self.engine)
        self.now = datetime.now(timezone.utc)
        self.user = uuid4()
        self.product = uuid4()
        self.warehouse = uuid4()
        self.supplier = uuid4()
        self.batch = uuid4()
        with self.sessions.begin() as session:
            session.add_all([
                UserModel(id=self.user, external_id="buyer", display_name="Buyer", role=UserRole.BUYER),
                ProductModel(id=self.product, sku="SKU", name="Product", unit="pcs"),
                WarehouseModel(id=self.warehouse, code="W", name="Warehouse"),
                SupplierModel(id=self.supplier, code="S", name="Supplier"),
            ])
            session.flush()
            session.add_all([
                SupplierProductModel(
                    id=uuid4(), supplier_id=self.supplier, product_id=self.product,
                    moq=Decimal("1"), package_size=Decimal("1"), lead_time_days=7,
                    is_primary=True,
                ),
                ImportBatchModel(
                    id=self.batch, source_type=ImportSourceType.SALES,
                    file_name="sales.xlsx", file_checksum=uuid4().hex,
                    status=ImportStatus.COMPLETED, imported_by=self.user,
                    imported_at=self.now - timedelta(days=1), row_count=5,
                ),
            ])
            session.flush()
            for index, quantity in enumerate((2, 2, 2, 20, -1), start=1):
                session.add(SalesTransactionModel(
                    id=uuid4(), import_batch_id=self.batch, source_row_number=index,
                    sold_at=self.now - timedelta(days=index),
                    product_id=self.product, warehouse_id=self.warehouse,
                    transaction_type=(TransactionType.SALE if quantity > 0 else TransactionType.RETURN),
                    quantity=Decimal(quantity),
                ))

        class Db:
            session_factory = self.sessions

        self.factory = create_application_uow_factory(Db())

    def test_run_read_list_and_explain(self):
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
        ))
        self.assertEqual(run.status, CalculationRunStatus.COMPLETED)
        self.assertEqual(run.import_batch_ids, {self.batch})
        info = GetCalculationRun(self.factory).execute(run.id)
        self.assertEqual(info.recommendation_count, 1)
        self.assertEqual(info.algorithm_version, "mvp-1")
        page = ListRecommendations(self.factory).execute(ListRecommendationsQuery(
            calculation_run_id=run.id, supplier_id=self.supplier, limit=1,
        ))
        self.assertEqual(page.total, 1)
        self.assertEqual(len(page.items), 1)
        explanation = ExplainRecommendation(self.factory).execute(page.items[0].id)
        self.assertEqual(len(explanation.anomalies), 1)
        self.assertEqual(explanation.anomalies[0].original_quantity, Decimal("20"))
        self.assertGreater(explanation.forecast.forecast_quantity, 0)
        self.assertIn("MOQ", explanation.formula)

    def test_failure_is_persisted(self):
        class BrokenPipeline:
            def calculate(self, run, uow):
                raise RuntimeError("broken pipeline")

        with self.assertRaisesRegex(RuntimeError, "broken pipeline"):
            RunCalculation(self.factory, BrokenPipeline()).execute(
                RunCalculationCommand(user_id=self.user, horizon_days=30)
            )
        with self.sessions() as session:
            from backend.infrastructure.persistence.models.calculation import CalculationRunModel
            saved = session.query(CalculationRunModel).one()
            self.assertEqual(saved.status, CalculationRunStatus.FAILED)
            self.assertEqual(saved.error_details["message"], "broken pipeline")

    def test_missing_completed_import_is_failed_run(self):
        with self.sessions.begin() as session:
            session.get(ImportBatchModel, self.batch).status = ImportStatus.FAILED
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, horizon_days=30,
        ))
        self.assertEqual(run.status, CalculationRunStatus.FAILED)
        self.assertEqual(GetCalculationRun(self.factory).execute(run.id).recommendation_count, 0)

    def test_explicit_source_is_recorded_and_other_source_is_never_queried(self):
        batch = uuid4()
        with self.sessions.begin() as session:
            session.add(ImportBatchModel(id=batch, source_type=ImportSourceType.MONTHLY_SALES,
                                        file_name="monthly.xlsx", file_checksum=uuid4().hex,
                                        status=ImportStatus.COMPLETED, imported_by=self.user,
                                        imported_at=self.now - timedelta(days=1)))
            session.flush()
            session.add(MonthlySalesModel(import_batch_id=batch, source_row_number=1, product_id=self.product,
                                          warehouse_id=self.warehouse, quantity=Decimal(365),
                                          period_start=(self.now - timedelta(days=60)).date(),
                                          period_end=(self.now - timedelta(days=30)).date()))
        with patch.object(SqlAlchemySalesRepository, "list_monthly_sales", side_effect=AssertionError("wrong source")):
            transactions = RunCalculation(self.factory).execute(RunCalculationCommand(
                user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
                demand_source=DemandSource.TRANSACTIONS,
            ))
        self.assertEqual(transactions.parameters["demand_source"], "transactions")
        with patch.object(SqlAlchemySalesRepository, "list_transactions", side_effect=AssertionError("wrong source")):
            monthly = RunCalculation(self.factory).execute(RunCalculationCommand(
                user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
                demand_source=DemandSource.MONTHLY_SALES,
            ))
        self.assertEqual(monthly.parameters["demand_source"], "monthly_sales")
        with self.factory() as uow:
            forecast = uow.calculation_runs.get_forecast(monthly.id, self.product, self.warehouse)
        self.assertEqual(forecast.raw_demand, Decimal(30))
        with patch.object(SqlAlchemySalesRepository, "list_transactions", return_value=[]), \
                patch.object(SqlAlchemySalesRepository, "list_monthly_sales", side_effect=AssertionError("implicit fallback")):
            empty = RunCalculation(self.factory).execute(RunCalculationCommand(
                user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
                demand_source=DemandSource.TRANSACTIONS,
            ))
        self.assertEqual(GetCalculationRun(self.factory).execute(empty.id).recommendation_count, 0)
