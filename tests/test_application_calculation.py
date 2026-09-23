import unittest
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import create_engine, event

from backend.application.dto.calculation import RunCalculationCommand
from backend.application.use_cases.explain_recommendation import ExplainRecommendation
from backend.application.use_cases.get_calculation_run import GetCalculationRun
from backend.application.use_cases.get_demand_trends import GetDemandTrends
from backend.application.use_cases.list_recommendations import ListRecommendations, ListRecommendationsQuery
from backend.application.use_cases.run_calculation import RunCalculation
from backend.domain.entities.enums import CalculationRunStatus
from backend.domain.enums import ImportSourceType, ImportStatus, TransactionType, UserRole
from backend.infrastructure.persistence.database import create_session_factory
from backend.infrastructure.persistence.models import (
    Base, CategoryModel, ImportBatchModel, InventorySnapshotModel, ProductModel,
    SalesTransactionModel, SupplierModel,
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
        self.assertEqual(info.algorithm_version, "mvp-2")
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
        month = (self.now - timedelta(days=60)).date().replace(day=1)
        month_end = month.replace(day=monthrange(month.year, month.month)[1])
        with self.sessions.begin() as session:
            session.add(ImportBatchModel(id=batch, source_type=ImportSourceType.MONTHLY_SALES,
                                        file_name="monthly.xlsx", file_checksum=uuid4().hex,
                                        status=ImportStatus.COMPLETED, imported_by=self.user,
                                        imported_at=self.now - timedelta(days=1)))
            session.flush()
            session.add(MonthlySalesModel(import_batch_id=batch, source_row_number=1, product_id=self.product,
                                          warehouse_id=self.warehouse, quantity=Decimal(365),
                                          period_start=month, period_end=month_end))
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

    def test_run_excludes_one_customer_monthly_spike_from_saved_forecast(self):
        current = self.now.year * 12 + self.now.month - 1
        with self.sessions.begin() as session:
            session.query(SalesTransactionModel).delete()
            row_number = 1
            for offset in range(6, 0, -1):
                month_index = current - offset
                sold_at = datetime(month_index // 12, month_index % 12 + 1, 2,
                                   tzinfo=timezone.utc)
                copies = 10 if offset == 1 else 1
                for _ in range(copies):
                    session.add(SalesTransactionModel(
                        import_batch_id=self.batch, source_row_number=row_number,
                        sold_at=sold_at, product_id=self.product,
                        warehouse_id=self.warehouse, transaction_type=TransactionType.SALE,
                        quantity=Decimal("10"), anonymous_customer_id="anon-1",
                    ))
                    row_number += 1
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
        ))
        with self.factory() as uow:
            forecast = uow.calculation_runs.get_forecast(run.id, self.product, self.warehouse)
            anomalies = uow.calculation_runs.list_anomalies(run.id, self.product, self.warehouse)
        self.assertEqual({row.method for row in anomalies}, {"customer_period_iqr"})
        self.assertLess(forecast.anomaly_adjustment, 0)
        self.assertLess(forecast.cleaned_baseline, forecast.raw_demand)
        self.assertEqual(forecast.details["customer_check"], "checked")

    def test_run_infers_stockout_from_snapshots_and_records_source(self):
        current = self.now.year * 12 + self.now.month - 1
        donor_months = [current - 5, current - 4]
        outage_month = current - 3
        with self.sessions.begin() as session:
            session.query(SalesTransactionModel).delete()
            for row_number, month_index in enumerate(donor_months, start=1):
                session.add(SalesTransactionModel(
                    import_batch_id=self.batch, source_row_number=row_number,
                    sold_at=datetime(month_index // 12, month_index % 12 + 1, 2,
                                     tzinfo=timezone.utc),
                    product_id=self.product, warehouse_id=self.warehouse,
                    transaction_type=TransactionType.SALE, quantity=Decimal("30"),
                ))
            snapshot_dates = [
                datetime(donor_months[0] // 12, donor_months[0] % 12 + 1, 3, tzinfo=timezone.utc),
                datetime(outage_month // 12, outage_month % 12 + 1, 2, tzinfo=timezone.utc),
                datetime(outage_month // 12, outage_month % 12 + 1, 25, tzinfo=timezone.utc),
            ]
            for at, quantity in zip(snapshot_dates, (10, 0, 0)):
                session.add(InventorySnapshotModel(
                    import_batch_id=self.batch, product_id=self.product,
                    warehouse_id=self.warehouse, snapshot_at=at,
                    quantity_on_hand=Decimal(quantity), quantity_available=Decimal(quantity),
                ))
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
        ))
        with self.factory() as uow:
            forecast = uow.calculation_runs.get_forecast(run.id, self.product, self.warehouse)
        self.assertGreater(forecast.stockout_adjustment, 0)
        self.assertEqual({row["source"] for row in forecast.details["stockout_evidence"]}, {"inferred"})

    def test_run_applies_calculated_sustained_growth_and_saves_policy(self):
        current = self.now.year * 12 + self.now.month - 1
        with self.sessions.begin() as session:
            session.query(SalesTransactionModel).delete()
            for row_number, offset in enumerate(range(6, 0, -1), start=1):
                month_index = current - offset
                session.add(SalesTransactionModel(
                    import_batch_id=self.batch, source_row_number=row_number,
                    sold_at=datetime(month_index // 12, month_index % 12 + 1, 2,
                                     tzinfo=timezone.utc),
                    product_id=self.product, warehouse_id=self.warehouse,
                    transaction_type=TransactionType.SALE,
                    quantity=Decimal("30" if offset <= 3 else "10"),
                ))
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, warehouse_id=self.warehouse, horizon_days=30,
        ))
        with self.factory() as uow:
            forecast = uow.calculation_runs.get_forecast(run.id, self.product, self.warehouse)
            recommendation = uow.recommendations.list_for_run(run.id)[0][0]
        self.assertGreater(forecast.growth_rate, 0)
        self.assertEqual(forecast.details["growth_source"], "calculated")
        self.assertEqual(run.parameters["risk_policy"]["critical_threshold"], "0.85")
        self.assertEqual(recommendation.calculation_details["risk_policy"], run.parameters["risk_policy"])

    def test_category_trends_aggregate_saved_history_without_recalculation(self):
        category, second_product = uuid4(), uuid4()
        with self.sessions.begin() as session:
            session.add(CategoryModel(id=category, code="C", name="Category"))
            session.flush()
            session.get(ProductModel, self.product).category_id = category
            session.add(ProductModel(id=second_product, sku="SKU-2", name="Second", unit="pcs",
                                     category_id=category))
            session.flush()
            session.add(SupplierProductModel(
                supplier_id=self.supplier, product_id=second_product,
                moq=Decimal("1"), package_size=Decimal("1"), lead_time_days=7,
                is_primary=True,
            ))
            session.add(SalesTransactionModel(
                import_batch_id=self.batch, source_row_number=100,
                sold_at=self.now - timedelta(days=2), product_id=second_product,
                warehouse_id=self.warehouse, transaction_type=TransactionType.SALE,
                quantity=Decimal("8"),
            ))
        run = RunCalculation(self.factory).execute(RunCalculationCommand(
            user_id=self.user, warehouse_id=self.warehouse, category_id=category,
            horizon_days=30,
        ))
        points = GetDemandTrends(self.factory).execute(run.id, category_id=category)
        self.assertEqual(len(points), 12)
        with self.factory() as uow:
            forecasts = uow.calculation_runs.list_forecasts(run.id)
        self.assertEqual(len(forecasts), 2)
        self.assertEqual(sum((point.raw_demand for point in points), Decimal("0")),
                         sum((sum(Decimal(period["raw_demand"]) for period in
                                  forecast.details["monthly_history"])
                              for forecast in forecasts), Decimal("0")))
        self.assertEqual(GetDemandTrends(self.factory).execute(run.id, category_id=uuid4()), [])
        with self.sessions.begin() as session:
            session.get(ProductModel, self.product).category_id = None
        self.assertEqual(GetDemandTrends(self.factory).execute(run.id, category_id=category), points)
