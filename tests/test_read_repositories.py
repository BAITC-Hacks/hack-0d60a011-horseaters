"""Execute source queries against isolated SQLite, with real constraints and mapping."""

import subprocess
import sys
import unittest
from dataclasses import is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from backend.domain.entities.imports import MonthlySales, SalesTransaction
from backend.domain.enums import (
    GrowthSource, ImportSourceType, ImportStatus, MaterialRequirementStatus,
    StockoutSource, TransactionType, TransitStatus, UserRole,
)
from backend.domain.repositories.filters import AmbiguousSourceDataError
from backend.infrastructure.persistence.database import create_session_factory
from backend.infrastructure.persistence.inventory_repository import SqlAlchemyInventoryRepository
from backend.infrastructure.persistence.material_requirement_repository import SqlAlchemyMaterialRequirementRepository
from backend.infrastructure.persistence.models import (
    Base, CategoryModel, GrowthAssumptionModel, ImportBatchModel, InTransitItemModel,
    InventorySnapshotModel, MaterialRequirementModel, MonthlySalesModel, ProductModel,
    SalesTransactionModel, SeasonalityCoefficientModel, StockoutPeriodModel,
    SupplierModel, SupplierProductModel, UserModel, WarehouseModel,
)
from backend.infrastructure.persistence.product_repository import SqlAlchemyProductRepository
from backend.infrastructure.persistence.sales_repository import SqlAlchemySalesRepository
from backend.infrastructure.persistence.seasonality_repository import SqlAlchemySeasonalityRepository
from backend.infrastructure.persistence.supplier_repository import SqlAlchemySupplierRepository
from backend.infrastructure.persistence.unit_of_work import RepositoryFactories, SqlAlchemyUnitOfWork


NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)
DAY = timedelta(days=1)
ROOT = Path(__file__).resolve().parents[1]


class ReadRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        # Only the source tables, in a new private in-memory database each time.
        for table in Base.metadata.sorted_tables:
            if table.name in {
                "users", "categories", "products", "warehouses", "suppliers", "supplier_products",
                "import_batches", "sales_transactions", "monthly_sales", "inventory_snapshots",
                "stockout_periods", "in_transit_items", "seasonality_coefficients",
                "growth_assumptions", "material_requirements",
            }:
                table.create(self.engine)
        self.session = Session(self.engine, autoflush=True)
        self.addCleanup(self.session.close)
        self.user = self.insert(UserModel, external_id="test", display_name="Test", role=UserRole.BUYER)
        self.category = self.insert(CategoryModel, code="category", name="Category")
        self.product = self.insert(ProductModel, sku="one", name="One", unit="pcs", category_id=self.category)
        self.other_product = self.insert(ProductModel, sku="two", name="Two", unit="pcs")
        self.warehouse = self.insert(WarehouseModel, code="one", name="One")
        self.other_warehouse = self.insert(WarehouseModel, code="two", name="Two")
        self.supplier = self.insert(SupplierModel, code="one", name="One")
        self.batches = {source: self.batch(source=source) for source in ImportSourceType}
        self.failed = self.batch(status=ImportStatus.FAILED)
        self.processing = self.batch(status=ImportStatus.PROCESSING)
        self.pending = self.batch(status=ImportStatus.PENDING)
        self.row_number = 0
        self.products = SqlAlchemyProductRepository(self.session)
        self.sales = SqlAlchemySalesRepository(self.session)
        self.inventory = SqlAlchemyInventoryRepository(self.session)
        self.suppliers = SqlAlchemySupplierRepository(self.session)
        self.seasonality = SqlAlchemySeasonalityRepository(self.session)
        self.materials = SqlAlchemyMaterialRequirementRepository(self.session)

    def insert(self, model, **values):
        values.setdefault("id", uuid4())
        for name in ("created_at", "updated_at"):
            if name in model.__table__.c:
                values.setdefault(name, NOW)
        self.session.execute(model.__table__.insert().values(**values))
        return values["id"]

    def batch(self, *, status=ImportStatus.COMPLETED, source=ImportSourceType.SALES):
        return self.insert(
            ImportBatchModel, source_type=source, status=status, imported_by=self.user,
            file_name="synthetic.xlsx", file_checksum=uuid4().hex, imported_at=NOW,
        )

    def fact(self, model, **overrides):
        self.row_number += 1
        defaults = {
            SalesTransactionModel: dict(source_row_number=self.row_number, sold_at=NOW,
                                        transaction_type=TransactionType.SALE, quantity=Decimal("2")),
            MonthlySalesModel: dict(source_row_number=self.row_number, period_start=date(2026, 9, 1),
                                   period_end=date(2026, 9, 30), quantity=Decimal("120")),
            InventorySnapshotModel: dict(snapshot_at=NOW, quantity_on_hand=Decimal("9"),
                                         quantity_available=Decimal("7"), quantity_reserved=Decimal("2")),
            StockoutPeriodModel: dict(started_at=NOW, ended_at=None, source=StockoutSource.IMPORTED),
            InTransitItemModel: dict(supplier_id=self.supplier, destination_warehouse_id=self.warehouse,
                                    quantity=Decimal("3"), expected_at=NOW, status=TransitStatus.IN_TRANSIT),
            SeasonalityCoefficientModel: dict(month=9, coefficient=Decimal("1.25"),
                                             valid_from=date(2026, 1, 1), version=1),
            GrowthAssumptionModel: dict(growth_rate=Decimal("0.08"), valid_from=date(2026, 1, 1),
                                       source=GrowthSource.IMPORTED),
            MaterialRequirementModel: dict(required_at=NOW, required_quantity=Decimal("4"),
                                          status=MaterialRequirementStatus.PLANNED),
        }
        sources = dict(zip(defaults, (
            ImportSourceType.SALES, ImportSourceType.MONTHLY_SALES, ImportSourceType.INVENTORY,
            ImportSourceType.STOCKOUT, ImportSourceType.IN_TRANSIT, ImportSourceType.SEASONALITY,
            ImportSourceType.GROWTH, ImportSourceType.MATERIAL_REQUIREMENTS,
        )))
        values = dict(defaults[model], product_id=self.product, import_batch_id=self.batches[sources[model]])
        if "warehouse_id" in model.__table__.c:
            values["warehouse_id"] = self.warehouse
        values.update(overrides)
        return self.insert(model, **values)

    @staticmethod
    def ids(rows):
        return {row.id for row in rows}

    def test_snapshot_is_latest_at_or_before_cutoff_for_exact_pair(self):
        old = self.fact(InventorySnapshotModel, snapshot_at=NOW - DAY)
        current = self.fact(InventorySnapshotModel)
        self.fact(InventorySnapshotModel, snapshot_at=NOW + DAY)
        self.fact(InventorySnapshotModel, snapshot_at=NOW, product_id=self.other_product)
        self.fact(InventorySnapshotModel, snapshot_at=NOW, warehouse_id=self.other_warehouse)
        self.fact(InventorySnapshotModel, snapshot_at=NOW + DAY / 2, import_batch_id=self.failed)
        self.assertIsNone(self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW - 2 * DAY))
        self.assertEqual(self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW - DAY / 2).id, old)
        # The same instant expressed in UTC+5, with a later snapshot present.
        at = NOW.astimezone(timezone(timedelta(hours=5)))
        result = self.inventory.get_latest_snapshot(self.product, self.warehouse, at)
        self.assertEqual(result.id, current)
        self.assertEqual(result.quantity_available, Decimal("7"))
        self.assertEqual(result.snapshot_at, NOW)
        self.assertEqual(self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW + DAY / 2).id, current)

    def test_snapshot_tie_requires_explicit_import_selection(self):
        first = self.fact(InventorySnapshotModel)
        other_batch = self.batch(source=ImportSourceType.INVENTORY)
        self.fact(InventorySnapshotModel, import_batch_id=other_batch)
        with self.assertRaises(AmbiguousSourceDataError):
            self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW)
        result = self.inventory.get_latest_snapshot(
            self.product, self.warehouse, NOW, import_batch_ids=[self.batches[ImportSourceType.INVENTORY]],
        )
        self.assertEqual(result.id, first)
        self.assertIsNone(self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW, import_batch_ids=[]))

    def test_stockouts_overlap_include_open_intervals_and_exclude_boundary_touches(self):
        end = NOW + DAY
        expected = {
            self.fact(StockoutPeriodModel, started_at=NOW - DAY, ended_at=NOW + DAY / 2),
            self.fact(StockoutPeriodModel, started_at=NOW - DAY, ended_at=end + DAY),
            self.fact(StockoutPeriodModel, started_at=NOW + DAY / 4, ended_at=NOW + DAY / 2),
            self.fact(StockoutPeriodModel, started_at=NOW - DAY, ended_at=None),
            self.fact(StockoutPeriodModel, started_at=NOW, ended_at=None, import_batch_id=None,
                      source=StockoutSource.INFERRED),
        }
        self.fact(StockoutPeriodModel, started_at=NOW - DAY, ended_at=NOW)
        self.fact(StockoutPeriodModel, started_at=end, ended_at=None)
        self.fact(StockoutPeriodModel, import_batch_id=self.failed)
        self.fact(StockoutPeriodModel, product_id=self.other_product)
        self.fact(StockoutPeriodModel, warehouse_id=self.other_warehouse)
        rows = self.inventory.list_stockout_periods(NOW, end, product_id=self.product, warehouse_id=self.warehouse)
        self.assertEqual(self.ids(rows), expected)
        self.assertEqual(self.inventory.list_stockout_periods(NOW, end, import_batch_ids=[]), [])
        scoped = self.inventory.list_stockout_periods(
            NOW, end, product_id=self.product, warehouse_id=self.warehouse,
            import_batch_ids=[self.batches[ImportSourceType.STOCKOUT]],
        )
        self.assertEqual(len(scoped), 4)  # NULL batch is outside an explicit whitelist.

    def test_active_transit_statuses_dates_and_unknown_dates(self):
        expected = {
            self.fact(InTransitItemModel, status=TransitStatus.PLANNED),
            self.fact(InTransitItemModel, status=TransitStatus.IN_TRANSIT, expected_at=NOW + DAY / 2),
        }
        unknown = self.fact(InTransitItemModel, expected_at=None)
        for status in (TransitStatus.RECEIVED, TransitStatus.CANCELLED):
            self.fact(InTransitItemModel, status=status)
            self.fact(InTransitItemModel, status=status, expected_at=None)
        self.fact(InTransitItemModel, expected_at=NOW + DAY)
        self.fact(InTransitItemModel, expected_at=NOW - DAY)
        self.fact(InTransitItemModel, import_batch_id=self.processing)
        self.fact(InTransitItemModel, product_id=self.other_product)
        self.fact(InTransitItemModel, destination_warehouse_id=self.other_warehouse)
        args = dict(product_id=self.product, warehouse_id=self.warehouse,
                    expected_from=NOW, expected_before=NOW + DAY)
        rows = self.inventory.list_active_in_transit(**args)
        self.assertEqual(self.ids(rows), expected)
        self.assertTrue(all(row.expected_at is not None for row in rows))
        self.assertEqual(self.ids(self.inventory.list_active_in_transit(**args, include_undated=True)),
                         expected | {unknown})

    def test_sales_and_monthly_are_distinct_sources_with_independent_filters(self):
        sale = self.fact(SalesTransactionModel)
        returned = self.fact(SalesTransactionModel, sold_at=NOW + DAY / 2,
                             transaction_type=TransactionType.RETURN, quantity=Decimal("-1"),
                             original_transaction_id=sale)
        self.fact(SalesTransactionModel, sold_at=NOW + DAY)
        self.fact(SalesTransactionModel, sold_at=NOW - DAY)
        self.fact(SalesTransactionModel, product_id=self.other_product)
        self.fact(SalesTransactionModel, warehouse_id=self.other_warehouse)
        for batch in (self.failed, self.processing, self.pending):
            self.fact(SalesTransactionModel, import_batch_id=batch)
        monthly = self.fact(MonthlySalesModel)
        global_monthly = self.fact(MonthlySalesModel, warehouse_id=None)
        other_monthly = self.fact(MonthlySalesModel, warehouse_id=self.other_warehouse)
        self.fact(MonthlySalesModel, period_start=date(2026, 10, 1), period_end=date(2026, 10, 31))
        self.fact(MonthlySalesModel, period_start=date(2026, 8, 1), period_end=date(2026, 8, 31))
        self.fact(MonthlySalesModel, import_batch_id=self.failed)
        self.fact(MonthlySalesModel, product_id=self.other_product)
        rows = self.sales.list_transactions(NOW, NOW + DAY, product_id=self.product, warehouse_id=self.warehouse)
        self.assertEqual(self.ids(rows), {sale, returned})
        self.assertTrue(all(isinstance(row, SalesTransaction) for row in rows))
        self.assertEqual(sum(row.quantity for row in rows), Decimal("1"))
        self.assertEqual(self.ids(self.sales.list_transactions(
            NOW, NOW + DAY, product_id=self.product, warehouse_id=self.warehouse,
            transaction_type=TransactionType.RETURN,
        )), {returned})
        args = dict(start=date(2026, 9, 30), end=date(2026, 9, 30), product_id=self.product)
        aggregates = self.sales.list_monthly_sales(**args)
        self.assertEqual(self.ids(aggregates), {monthly, global_monthly, other_monthly})
        self.assertTrue(all(isinstance(row, MonthlySales) for row in aggregates))
        self.assertEqual(self.ids(self.sales.list_monthly_sales(**args, warehouse_id=None)), {global_monthly})
        exact = self.sales.list_monthly_sales(**args, warehouse_id=self.warehouse)
        self.assertEqual(self.ids(exact), {monthly})
        self.assertEqual(exact[0].quantity, Decimal("120"))  # No prorating for the one-day overlap.
        self.assertEqual(self.sales.list_transactions(NOW, NOW + DAY, import_batch_ids=[]), [])

    def test_supplier_terms_preserve_values_and_require_active_supplier_and_terms(self):
        inactive_supplier = self.insert(SupplierModel, code="inactive", name="Inactive", is_active=False)
        other_supplier = self.insert(SupplierModel, code="other", name="Other")
        values = dict(product_id=self.product, moq=Decimal("12.5"), package_size=Decimal("2.5"),
                      lead_time_days=17, purchase_price=Decimal("4.75"), currency="KZT", priority=3)
        primary = self.insert(SupplierProductModel, **values, supplier_id=self.supplier, is_primary=True)
        self.insert(SupplierProductModel, **values, supplier_id=inactive_supplier)
        self.insert(SupplierProductModel, **values, supplier_id=other_supplier, is_active=False)
        rows = self.suppliers.list_terms(self.product)
        self.assertEqual(self.ids(rows), {primary})
        self.assertEqual((rows[0].moq, rows[0].package_size, rows[0].lead_time_days),
                         (Decimal("12.5"), Decimal("2.5"), 17))
        self.assertEqual(len(self.suppliers.list_terms(self.product, active_only=False)), 3)
        self.assertEqual(self.suppliers.list_terms(self.product, supplier_id=inactive_supplier), [])
        self.assertFalse(self.suppliers.get_by_id(inactive_supplier).is_active)
        self.assertIsNone(self.suppliers.get_by_id(uuid4()))

    def test_seasonality_uses_product_then_category_with_validity_and_no_implicit_version(self):
        category = self.fact(SeasonalityCoefficientModel, product_id=None, category_id=self.category)
        self.fact(SeasonalityCoefficientModel, valid_to=date(2026, 9, 22))
        self.fact(SeasonalityCoefficientModel, valid_from=date(2026, 9, 24))
        self.fact(SeasonalityCoefficientModel, month=10)
        self.fact(SeasonalityCoefficientModel, import_batch_id=self.failed)
        self.assertEqual(self.seasonality.get_coefficient(self.product, NOW.date()).id, category)
        product = self.fact(SeasonalityCoefficientModel, valid_from=NOW.date(), valid_to=NOW.date())
        self.assertEqual(self.seasonality.get_coefficient(self.product, NOW.date()).id, product)
        other = self.fact(SeasonalityCoefficientModel, version=2)
        self.assertEqual(self.ids(self.seasonality.list_coefficients(self.product, NOW.date())), {product, other})
        with self.assertRaises(AmbiguousSourceDataError):
            self.seasonality.get_coefficient(self.product, NOW.date())
        self.assertEqual(self.seasonality.get_coefficient(self.product, NOW.date(), version=2).id, other)
        self.assertIsNone(self.seasonality.get_coefficient(self.other_product, NOW.date()))

    def test_growth_filters_are_exact_and_preserve_competing_sources_and_null_warehouse(self):
        product = self.fact(GrowthAssumptionModel, source=GrowthSource.MANUAL, import_batch_id=None)
        global_product = self.fact(GrowthAssumptionModel, warehouse_id=None)
        category = self.fact(GrowthAssumptionModel, product_id=None, category_id=self.category, warehouse_id=None)
        both = self.fact(GrowthAssumptionModel, category_id=self.category, valid_to=NOW.date())
        self.fact(GrowthAssumptionModel, valid_to=date(2026, 9, 22))
        self.fact(GrowthAssumptionModel, valid_from=date(2026, 9, 24))
        self.fact(GrowthAssumptionModel, import_batch_id=self.failed)
        self.assertEqual(self.ids(self.seasonality.list_growth_assumptions(NOW.date())),
                         {product, global_product, category, both})
        self.assertEqual(self.ids(self.seasonality.list_growth_assumptions(
            NOW.date(), product_id=self.product, category_id=None, warehouse_id=self.warehouse,
        )), {product})
        self.assertEqual(self.ids(self.seasonality.list_growth_assumptions(NOW.date(), warehouse_id=None)),
                         {global_product, category})
        self.assertEqual(self.ids(self.seasonality.list_growth_assumptions(NOW.date(), source=GrowthSource.MANUAL)),
                         {product})

    def test_material_requirements_filter_dates_status_and_dimensions(self):
        planned = self.fact(MaterialRequirementModel)
        fulfilled = self.fact(MaterialRequirementModel, status=MaterialRequirementStatus.FULFILLED)
        cancelled = self.fact(MaterialRequirementModel, status=MaterialRequirementStatus.CANCELLED)
        self.fact(MaterialRequirementModel, required_at=NOW + DAY)
        self.fact(MaterialRequirementModel, required_at=NOW - DAY)
        self.fact(MaterialRequirementModel, product_id=self.other_product)
        self.fact(MaterialRequirementModel, warehouse_id=self.other_warehouse)
        self.fact(MaterialRequirementModel, import_batch_id=self.failed)
        args = dict(start=NOW, end=NOW + DAY, product_id=self.product, warehouse_id=self.warehouse)
        self.assertEqual(self.ids(self.materials.list_requirements(**args)), {planned})
        self.assertEqual(self.ids(self.materials.list_requirements(**args, status=None)), {planned, fulfilled, cancelled})

    def test_product_filters_include_explicit_uncategorized_and_inactive_lookup(self):
        inactive = self.insert(ProductModel, sku="inactive", name="Inactive", unit="pcs", is_active=False)
        self.assertEqual(self.ids(self.products.list_products()), {self.product, self.other_product})
        self.assertEqual(self.ids(self.products.list_products(category_id=None)), {self.other_product})
        self.assertEqual(self.ids(self.products.list_products(category_id=self.category)), {self.product})
        self.assertEqual(self.products.get_by_sku("inactive").id, inactive)
        self.assertEqual(self.ids(self.products.list_products(is_active=False)), {inactive})
        self.assertEqual(len(self.products.list_products(is_active=None)), 3)
        self.assertIsNone(self.products.get_by_id(uuid4()))

    def test_all_repositories_are_read_only_and_return_detached_domain_data(self):
        self.fact(SalesTransactionModel)
        self.fact(MonthlySalesModel)
        self.fact(InventorySnapshotModel)
        self.fact(StockoutPeriodModel)
        self.fact(InTransitItemModel)
        self.fact(SeasonalityCoefficientModel)
        self.fact(GrowthAssumptionModel)
        self.fact(MaterialRequirementModel)
        self.insert(SupplierProductModel, supplier_id=self.supplier, product_id=self.product, moq=1, lead_time_days=2)
        self.session.commit()
        pending = ProductModel(sku="pending", name="Pending", unit="pcs")
        self.session.add(pending)
        statements = []
        postgres_queries = []

        @event.listens_for(self.session, "do_orm_execute")
        def compile_for_postgres(execution):
            postgres_queries.append(str(execution.statement.compile(dialect=postgresql.dialect())))

        @event.listens_for(self.engine, "before_cursor_execute")
        def capture(connection, cursor, statement, parameters, context, many):
            statements.append(statement)

        with patch.object(self.session, "commit", side_effect=AssertionError("Unexpected commit")), \
                patch.object(self.session, "rollback", side_effect=AssertionError("Unexpected rollback")), \
                patch.object(self.session, "close", side_effect=AssertionError("Unexpected close")):
            rows = [self.products.get_by_id(self.product), self.suppliers.get_by_id(self.supplier)]
            rows += self.sales.list_transactions(NOW, NOW + DAY)
            rows += self.sales.list_monthly_sales(NOW.date(), NOW.date())
            rows += [self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW)]
            rows += self.inventory.list_stockout_periods(NOW, NOW + DAY)
            rows += self.inventory.list_active_in_transit()
            rows += self.suppliers.list_terms(self.product)
            rows += self.seasonality.list_coefficients(self.product, NOW.date())
            rows += self.seasonality.list_growth_assumptions(NOW.date())
            rows += self.materials.list_requirements(NOW, NOW + DAY)
        self.assertIn(pending, self.session.new)
        self.assertTrue(statements)
        self.assertEqual(len(postgres_queries), len(statements))
        self.assertTrue(all(sql.lstrip().upper().startswith("SELECT") for sql in statements))
        self.session.close()
        for row in rows:
            self.assertTrue(is_dataclass(row))
            self.assertIsNone(inspect(row, raiseerr=False))
            self.assertIsNotNone(row.id)
        self.assertEqual(rows[2].quantity, Decimal("2"))
        self.assertIs(rows[2].transaction_type, TransactionType.SALE)

    def test_invalid_ranges_and_naive_datetimes_are_rejected(self):
        with self.assertRaises(ValueError):
            self.sales.list_transactions(NOW, NOW)
        with self.assertRaises(ValueError):
            self.inventory.list_stockout_periods(NOW + DAY, NOW)
        with self.assertRaises(ValueError):
            self.inventory.get_latest_snapshot(self.product, self.warehouse, NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            self.inventory.list_active_in_transit(expected_from=NOW, expected_before=NOW)
        with self.assertRaises(ValueError):
            self.materials.list_requirements(NOW, NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            self.sales.list_monthly_sales(date(2026, 10, 1), date(2026, 9, 1))
        with self.assertRaises(TypeError):
            self.seasonality.list_coefficients(self.product, NOW)

    def test_existing_inventory_read_api_preserves_inclusive_boundaries(self):
        ended = self.fact(StockoutPeriodModel, started_at=NOW - DAY, ended_at=NOW)
        started = self.fact(StockoutPeriodModel, started_at=NOW + DAY)
        self.fact(StockoutPeriodModel, import_batch_id=self.failed)
        args = dict(started_at=NOW, ended_at=NOW + DAY)
        positional = self.inventory.list_stockout_periods(self.product, self.warehouse, **args)
        named = self.inventory.list_stockout_periods(
            product_id=self.product, warehouse_id=self.warehouse, **args,
        )
        self.assertEqual(self.ids(positional), {ended, started})
        self.assertEqual(self.ids(named), {ended, started})
        mixed_ids = self.inventory.list_stockout_periods(self.product, warehouse_id=self.warehouse, **args)
        self.assertEqual(self.ids(mixed_ids), {ended, started})
        with self.assertRaises(TypeError):
            self.inventory.list_stockout_periods(NOW, NOW + DAY, **args)
        with self.assertRaises(TypeError):
            self.inventory.list_stockout_periods(self.product, self.warehouse, started_at=NOW)
        with self.assertRaises(TypeError):
            self.inventory.list_stockout_periods(self.product, self.warehouse, product_id=self.product, **args)
        at_end = self.fact(InventorySnapshotModel, snapshot_at=NOW + DAY)
        self.fact(InventorySnapshotModel, snapshot_at=NOW + DAY, import_batch_id=self.processing)
        self.assertEqual(self.ids(self.inventory.list_snapshots(self.product, self.warehouse, **args)), {at_end})
        at_eta = self.fact(InTransitItemModel, expected_at=NOW + DAY)
        unknown = self.fact(InTransitItemModel, expected_at=None)
        self.fact(InTransitItemModel, expected_at=NOW + DAY, import_batch_id=self.pending)
        self.assertEqual(self.ids(self.inventory.list_open_in_transit(
            self.product, self.warehouse, expected_by=NOW + DAY,
        )), {at_eta, unknown})

    def test_uow_injects_same_session_into_all_six_repositories(self):
        self.session.commit()
        unused = lambda session: object()
        factories = RepositoryFactories(
            imports=unused, orders=unused, recommendations=unused, calculation_runs=unused,
            sales=SqlAlchemySalesRepository, inventory=SqlAlchemyInventoryRepository,
            suppliers=SqlAlchemySupplierRepository, products=SqlAlchemyProductRepository,
            seasonality=SqlAlchemySeasonalityRepository,
            material_requirements=SqlAlchemyMaterialRequirementRepository,
        )
        with SqlAlchemyUnitOfWork(create_session_factory(self.engine), factories) as uow:
            repositories = [uow.products, uow.sales, uow.inventory, uow.suppliers, uow.seasonality, uow.material_requirements]
            self.assertEqual(len({id(repository.session) for repository in repositories}), 1)
            product = uow.products.get_by_id(self.product)
            self.assertEqual(product.sku, "one")
        self.assertEqual(product.sku, "one")

    def test_domain_ports_import_without_sqlalchemy(self):
        modules = ("product", "sales", "inventory", "supplier", "seasonality", "material_requirement")
        code = "\n".join(f"import backend.domain.repositories.{name}_repository" for name in modules)
        result = subprocess.run([sys.executable, "-B", "-S", "-c", code], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
