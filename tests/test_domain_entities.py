import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from backend.domain import entities
from backend.domain.entities import (
    Category, GrowthAssumption, ImportBatch, InventorySnapshot, InTransitItem,
    MaterialRequirement, MonthlySales, Product, SalesTransaction,
    SeasonalityCoefficient, StockoutPeriod, Supplier, SupplierProduct, User, Warehouse,
)
from backend.domain.enums import (
    GrowthSource, ImportSourceType, ImportStatus, MaterialRequirementStatus,
    StockoutSource, TransactionType, TransitStatus, UserRole,
)


class DomainEntityTests(unittest.TestCase):
    def setUp(self):
        self.product_id = uuid4()
        self.warehouse_id = uuid4()
        self.batch_id = uuid4()
        self.now = datetime(2026, 9, 23, tzinfo=timezone.utc)
        self.today = self.now.date()
        self.sale = SalesTransaction(
            import_batch_id=self.batch_id, source_row_number=1, sold_at=self.now,
            product_id=self.product_id, warehouse_id=self.warehouse_id,
            transaction_type=TransactionType.SALE, quantity=Decimal("2.5"),
        )
        self.terms = SupplierProduct(
            supplier_id=uuid4(), product_id=self.product_id,
            moq=Decimal("1"), lead_time_days=0,
        )
        self.monthly = MonthlySales(
            import_batch_id=self.batch_id, source_row_number=1,
            product_id=self.product_id, period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30), quantity=Decimal("12.25"),
        )
        self.stockout = StockoutPeriod(
            product_id=self.product_id, warehouse_id=self.warehouse_id,
            started_at=self.now, source=StockoutSource.INFERRED,
        )
        self.seasonality = SeasonalityCoefficient(
            import_batch_id=self.batch_id, product_id=self.product_id, month=9,
            coefficient=Decimal("1.25"), valid_from=self.today, version=1,
        )
        self.growth = GrowthAssumption(
            product_id=self.product_id, growth_rate=Decimal("0.08"),
            valid_from=self.today, source=GrowthSource.MANUAL,
        )
        self.transit = InTransitItem(
            import_batch_id=self.batch_id, supplier_id=uuid4(),
            product_id=self.product_id, destination_warehouse_id=self.warehouse_id,
            quantity=Decimal("5"), status=TransitStatus.IN_TRANSIT,
        )
        self.material = MaterialRequirement(
            import_batch_id=self.batch_id, product_id=self.product_id,
            warehouse_id=self.warehouse_id, required_quantity=Decimal("4"),
            required_at=self.now, status=MaterialRequirementStatus.PLANNED,
        )

    def assert_invalid_changes(self, entity, *changes):
        for change in changes:
            with self.subTest(entity=type(entity).__name__, changes=change):
                with self.assertRaises((TypeError, ValueError)):
                    replace(entity, **change)

    def test_all_fifteen_entities_can_be_constructed(self):
        values = [
            User(external_id="buyer-1", display_name="Buyer", role=UserRole.BUYER),
            Category(code="cat", name="Category"),
            Product(sku="sku", name="Product", unit="pcs"),
            Warehouse(code="wh", name="Warehouse"),
            Supplier(code="supplier", name="Supplier"),
            self.terms,
            ImportBatch(
                source_type=ImportSourceType.SALES, file_name="test.xlsx",
                file_checksum="a" * 64, status=ImportStatus.PENDING,
                imported_by=uuid4(), imported_at=self.now,
            ),
            self.sale, self.monthly,
            InventorySnapshot(
                import_batch_id=self.batch_id, product_id=self.product_id,
                warehouse_id=self.warehouse_id, snapshot_at=self.now,
                quantity_on_hand=Decimal("5"), quantity_available=Decimal("4"),
            ),
            self.stockout, self.transit, self.seasonality, self.growth, self.material,
        ]
        self.assertTrue({type(value).__name__ for value in values} <= set(entities.__all__))
        self.assertEqual(len({value.id for value in values}), 15)
        for value in values:
            self.assertIsInstance(value.id, UUID)

    def test_identity_and_utc_timestamp_defaults(self):
        first = Product(sku="one", name="One", unit="pcs")
        second = Product(sku="two", name="Two", unit="pcs")
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.created_at.utcoffset(), timedelta(0))
        self.assertEqual(first.updated_at.utcoffset(), timedelta(0))
        self.assertEqual(replace(first, name="Updated").id, first.id)

    def test_sale_and_return_signs_and_reference(self):
        returned = replace(
            self.sale, transaction_type=TransactionType.RETURN,
            quantity=Decimal("-1"), original_transaction_id=self.sale.id,
        )
        self.assertEqual(returned.original_transaction_id, self.sale.id)
        self.assert_invalid_changes(
            self.sale, {"quantity": Decimal("0")}, {"quantity": Decimal("-1")},
            {"original_transaction_id": uuid4()}, {"unit_price": Decimal("-1")},
        )
        self.assert_invalid_changes(
            returned, {"quantity": Decimal("0")}, {"quantity": Decimal("1")},
        )

    def test_supplier_terms(self):
        self.assertEqual(self.terms.package_size, Decimal("1"))
        self.assertEqual(self.terms.priority, 100)
        self.assert_invalid_changes(
            self.terms, {"moq": Decimal("0")}, {"package_size": Decimal("-1")},
            {"lead_time_days": -1}, {"purchase_price": Decimal("-1")},
        )

    def test_monthly_sales_period_and_optional_warehouse(self):
        self.assertIsNone(self.monthly.warehouse_id)
        replace(self.monthly, period_end=self.monthly.period_start)
        self.assert_invalid_changes(
            self.monthly, {"period_end": date(2026, 8, 31)},
            {"period_start": self.now},
        )

    def test_stockout_period_and_confidence(self):
        for confidence in (Decimal("0"), Decimal("1")):
            replace(self.stockout, confidence=confidence, ended_at=self.now + timedelta(days=1))
        self.assert_invalid_changes(
            self.stockout, {"ended_at": self.now},
            {"ended_at": self.now - timedelta(days=1)},
            {"confidence": Decimal("-0.1")}, {"confidence": Decimal("1.1")},
        )

    def test_seasonality_requires_exactly_one_level(self):
        replace(self.seasonality, product_id=None, category_id=uuid4(), month=12)
        self.assert_invalid_changes(
            self.seasonality, {"product_id": None}, {"category_id": uuid4()},
            {"month": 0}, {"month": 13}, {"coefficient": Decimal("0")},
        )

    def test_growth_allows_either_or_both_levels(self):
        self.assertIsNone(self.growth.warehouse_id)
        replace(self.growth, product_id=None, category_id=uuid4())
        replace(self.growth, category_id=uuid4())
        self.assert_invalid_changes(self.growth, {"product_id": None})

    def test_transit_and_material_quantities_are_positive(self):
        self.assert_invalid_changes(self.transit, {"quantity": Decimal("0")})
        self.assert_invalid_changes(self.material, {"required_quantity": Decimal("-1")})

    def test_decimal_values_are_finite_and_never_float(self):
        for invalid in (1.5, Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            self.assert_invalid_changes(self.sale, {"quantity": invalid})

    def test_datetime_requires_timezone_and_status_requires_enum(self):
        self.assert_invalid_changes(
            self.sale, {"sold_at": self.now.replace(tzinfo=None)},
            {"transaction_type": "sale"}, {"transaction_type": "typo"},
        )
        self.assert_invalid_changes(self.transit, {"status": "in_transit"})

    def test_changes_preserve_original_and_are_revalidated(self):
        with self.assertRaises(FrozenInstanceError):
            self.sale.quantity = Decimal("-1")
        changed = replace(self.sale, quantity=Decimal("3"))
        self.assertEqual(self.sale.quantity, Decimal("2.5"))
        self.assertEqual(changed.quantity, Decimal("3"))
        self.assert_invalid_changes(changed, {"quantity": Decimal("-1")})

    def test_entities_import_without_site_packages_or_infrastructure(self):
        script = (
            "import sys; import backend.domain.entities; "
            "assert not any(name.startswith(('sqlalchemy', 'pydantic', 'fastapi', "
            "'backend.infrastructure')) for name in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-S", "-c", script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
