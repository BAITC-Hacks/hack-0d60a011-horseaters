import subprocess
import sys
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from uuid import uuid4

from backend.domain.entities.imports import GrowthAssumption, InventorySnapshot, MonthlySales, SalesTransaction, StockoutPeriod
from backend.domain.entities.product import Product
from backend.domain.enums import GrowthSource, StockoutSource, TransactionType
from backend.domain.repositories.filters import AmbiguousSourceDataError
from backend.domain.services.demand_preparation import prepare_demand
from backend.domain.value_objects.demand import DemandConfig, DemandGroup, DemandSource


def at(month, day=1):
    return datetime(2026, month, day, tzinfo=timezone.utc)


class DemandPreparationTests(unittest.TestCase):
    def setUp(self):
        self.product = Product(sku="SKU-1", name="Product", unit="pcs")
        self.warehouse, self.run, self.batch = uuid4(), uuid4(), uuid4()
        self.group = DemandGroup(product=self.product, warehouse_id=self.warehouse)
        self.counter = 0

    def sale(self, month, quantity, **kwargs):
        self.counter += 1
        return SalesTransaction(import_batch_id=self.batch, source_row_number=self.counter,
                                product_id=self.product.id, warehouse_id=self.warehouse,
                                sold_at=at(month), transaction_type=TransactionType.SALE,
                                quantity=Decimal(quantity), **kwargs)

    def returned(self, month, quantity, original=None):
        self.counter += 1
        return SalesTransaction(import_batch_id=self.batch, source_row_number=self.counter,
                                product_id=self.product.id, warehouse_id=self.warehouse,
                                sold_at=at(month), transaction_type=TransactionType.RETURN,
                                quantity=-Decimal(quantity), original_transaction_id=original.id if original else None)

    def monthly(self, month, quantity, **kwargs):
        from calendar import monthrange
        self.counter += 1
        values = dict(import_batch_id=self.batch, source_row_number=self.counter,
                      product_id=self.product.id, warehouse_id=self.warehouse,
                      period_start=date(2026, month, 1), period_end=date(2026, month, monthrange(2026, month)[1]),
                      quantity=Decimal(quantity))
        return MonthlySales(**{**values, **kwargs})

    def snapshot(self, month, quantity):
        return InventorySnapshot(import_batch_id=self.batch, product_id=self.product.id, warehouse_id=self.warehouse,
                                 snapshot_at=at(month), quantity_on_hand=Decimal(quantity), quantity_available=Decimal(quantity))

    def prepare(self, **kwargs):
        arguments = dict(calculation_run_id=self.run, source=DemandSource.TRANSACTIONS,
                         start=date(2026, 1, 1), end=date(2026, 6, 30), source_cutoff_at=at(8), groups=[self.group])
        return prepare_demand(**{**arguments, **kwargs})

    def series(self, **kwargs):
        return self.prepare(**kwargs).series[0]

    def test_source_selection_never_sums_transactions_and_monthly_rows(self):
        data = dict(transactions=[self.sale(1, "10")], monthly_sales=[self.monthly(1, "999")])
        self.assertEqual(self.series(**data).periods[0].raw_demand, Decimal("10"))
        monthly = self.prepare(source=DemandSource.MONTHLY_SALES, **data)
        self.assertEqual(monthly.series[0].periods[0].raw_demand, Decimal("999"))
        self.assertEqual(monthly.parameters["demand_source"], "monthly_sales")
        self.assertEqual(monthly.parameters["return_handling"], "unavailable_monthly_aggregate")
        self.assertIn("monthly_sales_has_no_transaction_return_or_customer_details", monthly.series[0].limitations)

    def test_complete_calendar_keeps_empty_periods_and_separate_warehouses(self):
        second = DemandGroup(product=self.product, warehouse_id=uuid4())
        result = self.prepare(groups=[second, self.group], transactions=[self.sale(2, "12")])
        by_warehouse = {row.warehouse_id: row for row in result.series}
        row = by_warehouse[self.warehouse]
        self.assertEqual([p.raw_demand for p in row.periods], [0, 12, 0, 0, 0, 0])
        self.assertEqual(row.periods[1].period_end, date(2026, 2, 28))
        self.assertEqual((row.sku, row.unit), ("SKU-1", "pcs"))
        self.assertFalse(row.periods[0].observed)
        self.assertTrue(all(p.raw_demand == 0 for p in by_warehouse[second.warehouse_id].periods))

    def test_full_and_partial_linked_returns_go_to_original_month(self):
        full, partial = self.sale(1, "10"), self.sale(2, "20")
        rows = [full, partial, self.returned(2, "10", full), self.returned(3, "3", partial), self.returned(4, "4", partial)]
        output = self.series(transactions=rows).periods
        self.assertEqual((output[0].raw_demand, output[0].return_adjustment, output[0].cleaned_demand), (10, -10, 0))
        self.assertEqual((output[1].return_adjustment, output[1].cleaned_demand), (-7, 13))
        self.assertEqual([p.return_adjustment for p in output[2:]], [0, 0, 0, 0])
        self.assertEqual((full.quantity, partial.quantity), (10, 20))

    def test_return_after_calendar_end_is_included_only_through_cutoff(self):
        sale = self.sale(1, "10")
        rows = [sale, self.returned(2, "4", sale), self.returned(3, "2", sale)]
        result = self.series(end=date(2026, 1, 31), source_cutoff_at=at(2, 15), transactions=rows)
        self.assertEqual(result.periods[0].return_adjustment, -4)

    def test_return_to_sale_outside_calendar_does_not_reduce_current_month(self):
        old = self.sale(1, "10")
        series = self.series(start=date(2026, 2, 1), transactions=[old, self.sale(2, "5"), self.returned(2, "3", old)])
        self.assertEqual(series.periods[0].cleaned_demand, 5)
        self.assertIn("linked_return_targets_sale_outside_calendar", series.limitations)

    def test_unlinked_return_stays_in_own_month_and_floor_is_explained(self):
        output = self.series(transactions=[self.sale(1, "5"), self.returned(1, "8"), self.returned(2, "2")]).periods
        self.assertEqual((output[0].return_adjustment, output[0].nonnegative_adjustment, output[0].cleaned_demand), (-8, 3, 0))
        self.assertEqual((output[1].return_adjustment, output[1].nonnegative_adjustment), (-2, 2))

    def test_missing_or_cross_warehouse_reference_is_not_silently_unlinked(self):
        sale = self.sale(1, "10")
        returned = self.returned(2, "2", sale)
        with self.assertRaisesRegex(ValueError, "missing"):
            self.series(transactions=[returned])
        with self.assertRaisesRegex(ValueError, "same SKU and warehouse"):
            self.series(transactions=[sale, replace(returned, warehouse_id=uuid4())])

    def test_single_spike_is_replaced_only_in_calculation_and_audited(self):
        rows = [self.sale(1, str(value)) for value in [9, 10, 10, 11, 10, 10, 100]]
        series = self.series(transactions=rows)
        self.assertEqual(len(series.anomalies), 1)
        anomaly = series.anomalies[0]
        self.assertEqual((anomaly.original_quantity, anomaly.replacement_quantity), (100, 10))
        self.assertEqual(anomaly.sales_transaction_id, rows[-1].id)
        self.assertEqual(series.periods[0].anomaly_adjustment, -90)
        self.assertEqual(rows[-1].quantity, 100)

    def test_short_sparse_and_zero_iqr_series_do_not_flag_all_positive_values(self):
        for values in ([10, 100], [10, 10, 10, 10]):
            with self.subTest(values=values):
                series = self.series(transactions=[self.sale(1, str(value)) for value in values])
                self.assertEqual(series.anomalies, ())
        monthly = self.series(source=DemandSource.MONTHLY_SALES,
                              monthly_sales=[self.monthly(2, "10"), self.monthly(5, "100")])
        self.assertEqual(monthly.period_anomalies, ())
        rows = [self.sale(1, str(value)) for value in [10, 10, 10, 10, 10, 40]]
        self.assertEqual(len(self.series(transactions=rows).anomalies), 1)

    def test_customer_concentration_detects_split_documents_in_synthetic_data(self):
        rows = [self.sale(month, "10", anonymous_customer_id="anonymous-1") for month in range(1, 5)]
        rows += [self.sale(5, "10", anonymous_customer_id="anonymous-1") for _ in range(10)]
        series = self.series(transactions=rows)
        self.assertEqual(series.customer_check, "checked")
        self.assertEqual(series.periods[4].cleaned_demand, 10)
        self.assertEqual({row.method for row in series.anomalies}, {"customer_period_iqr"})
        without_ids = [replace(row, anonymous_customer_id=None) for row in rows]
        unchecked = self.series(transactions=without_ids)
        self.assertEqual(unchecked.customer_check, "unavailable_no_customer_ids")
        self.assertEqual(unchecked.periods[4].cleaned_demand, 100)

    def test_monthly_anomaly_has_a_period_audit_without_fake_transaction_id(self):
        rows = [self.monthly(month, str(value)) for month, value in enumerate([10, 10, 10, 10, 100, 10], 1)]
        series = self.series(source=DemandSource.MONTHLY_SALES, monthly_sales=rows)
        self.assertEqual(series.anomalies, ())
        self.assertEqual(len(series.period_anomalies), 1)
        self.assertEqual(series.period_anomalies[0].source_row_ids, (rows[4].id,))
        self.assertEqual(series.periods[4].anomaly_adjustment, -90)

    def stockout_data(self):
        return dict(source=DemandSource.MONTHLY_SALES,
                    monthly_sales=[self.monthly(1, "310"), self.monthly(2, "280")])

    def test_confirmed_stockout_compensates_missing_days_without_double_counting(self):
        outage = StockoutPeriod(product_id=self.product.id, warehouse_id=self.warehouse,
                                started_at=at(3), ended_at=at(4), source=StockoutSource.IMPORTED)
        overlapping = replace(outage, id=uuid4(), started_at=at(3, 15))
        series = self.series(**self.stockout_data(), stockouts=[outage, overlapping])
        march = series.periods[2]
        self.assertEqual((march.raw_demand, march.stockout_adjustment, march.cleaned_demand), (0, 310, 310))
        self.assertTrue(march.details["stockout"]["confirmed"])
        self.assertEqual(march.details["stockout"]["missing_days"], "31")

    def test_ordinary_zero_demand_without_inventory_is_not_compensated(self):
        series = self.series(**self.stockout_data())
        self.assertTrue(all(row.stockout_adjustment == 0 for row in series.periods))
        self.assertEqual(series.stockout_periods, ())

    def test_inferred_stockout_requires_repeated_inventory_evidence(self):
        snapshots = [self.snapshot(2, "10"), self.snapshot(3, "0"), self.snapshot(4, "0")]
        result = self.series(**self.stockout_data(), snapshots=snapshots)
        self.assertEqual(result.periods[2].stockout_adjustment, 310)
        self.assertFalse(result.periods[2].details["stockout"]["confirmed"])
        self.assertEqual(result.stockout_periods[0].source, StockoutSource.INFERRED)
        insufficient = self.series(**self.stockout_data(), snapshots=snapshots[:2])
        self.assertTrue(all(row.stockout_adjustment == 0 for row in insufficient.periods))

    def test_explicit_stockout_takes_priority_over_inventory_inference(self):
        explicit = StockoutPeriod(product_id=self.product.id, warehouse_id=self.warehouse,
                                 started_at=at(5), ended_at=at(6), source=StockoutSource.MANUAL)
        series = self.series(**self.stockout_data(), stockouts=[explicit],
                             snapshots=[self.snapshot(2, "10"), self.snapshot(3, "0"), self.snapshot(4, "0")])
        self.assertEqual(series.periods[2].stockout_adjustment, 0)
        self.assertEqual(series.stockout_periods, (explicit,))

    def test_stockout_without_comparable_periods_is_explained_but_not_invented(self):
        outage = StockoutPeriod(product_id=self.product.id, warehouse_id=self.warehouse,
                                started_at=at(3), source=StockoutSource.IMPORTED)
        series = self.series(stockouts=[outage])
        self.assertEqual(series.periods[2].stockout_adjustment, 0)
        self.assertEqual(series.periods[2].details["stockout"]["reason"], "insufficient_comparable_periods")

    def test_manual_and_imported_growth_are_explicit_and_do_not_change_raw_demand(self):
        for source in (GrowthSource.MANUAL, GrowthSource.IMPORTED):
            assumption = GrowthAssumption(product_id=self.product.id, warehouse_id=self.warehouse,
                                          growth_rate=Decimal("0.08"), valid_from=date(2026, 1, 1), source=source)
            series = self.series(transactions=[self.sale(1, "100")], growth_overrides={self.group.key: assumption})
            self.assertEqual((series.growth.factor, series.growth.source), (Decimal("1.08"), source))
            self.assertEqual((series.periods[0].raw_demand, series.periods[0].calculated_demand), (100, 108))

    def test_sustained_growth_is_bounded_and_short_history_is_neutral(self):
        rows = [self.monthly(month, str(days * rate)) for month, days, rate in
                [(1, 31, 10), (2, 28, 10), (3, 31, 10), (4, 30, 30), (5, 31, 30), (6, 30, 30)]]
        series = self.series(source=DemandSource.MONTHLY_SALES, monthly_sales=rows)
        self.assertEqual(series.growth.unclamped_factor, 3)
        self.assertEqual(series.growth.factor, 2)
        short = self.series(source=DemandSource.MONTHLY_SALES, monthly_sales=rows[:2], end=date(2026, 2, 28))
        self.assertEqual(short.growth.factor, 1)
        self.assertEqual(short.growth.reason, "insufficient_history")

    def test_growth_uses_cleaned_demand_instead_of_a_single_raw_spike(self):
        values = [310, 280, 310, 300, 310, 3000]
        rows = [self.monthly(month, str(value)) for month, value in enumerate(values, 1)]
        series = self.series(source=DemandSource.MONTHLY_SALES, monthly_sales=rows)
        self.assertLess(series.periods[-1].cleaned_demand, 400)
        self.assertEqual(series.growth.factor, 1)
        self.assertEqual(series.growth.reason, "no_sustained_change")

    def test_fully_returned_spike_is_not_an_anomaly_after_return_processing(self):
        rows = [self.sale(1, "10") for _ in range(4)]
        spike = self.sale(1, "100")
        series = self.series(transactions=[*rows, spike, self.returned(2, "100", spike)])
        self.assertEqual(series.anomalies, ())
        self.assertEqual(series.periods[0].cleaned_demand, 40)

    def test_results_are_deterministic_and_components_reconcile(self):
        rows = [self.sale(month, str(value)) for month, value in enumerate([10, 10, 10, 10, 100, 10], 1)]
        first = self.prepare(transactions=rows)
        with localcontext() as context:
            context.prec = 6
            second = self.prepare(transactions=list(reversed(rows)))
        self.assertEqual(first, second)
        for row in first.series[0].periods:
            total = row.raw_demand + row.return_adjustment + row.anomaly_adjustment + row.nonnegative_adjustment + row.stockout_adjustment
            self.assertEqual(row.cleaned_demand, total)
            self.assertEqual(row.calculated_demand, total + row.growth_adjustment)

    def test_null_warehouse_stays_separate_and_duplicate_aggregates_are_rejected(self):
        unassigned = DemandGroup(product=self.product, warehouse_id=None)
        rows = [self.monthly(1, "100"), self.monthly(1, "200", warehouse_id=None)]
        result = self.prepare(groups=[self.group, unassigned], source=DemandSource.MONTHLY_SALES, monthly_sales=rows)
        self.assertEqual({s.warehouse_id: s.periods[0].raw_demand for s in result.series}, {self.warehouse: 100, None: 200})
        with self.assertRaises(AmbiguousSourceDataError):
            self.series(source=DemandSource.MONTHLY_SALES, monthly_sales=[rows[0], self.monthly(1, "50")])

    def test_incomplete_months_and_bad_configuration_are_rejected(self):
        with self.assertRaises(ValueError):
            self.prepare(start=date(2026, 1, 15))
        with self.assertRaises(ValueError):
            self.prepare(source_cutoff_at=at(6, 20))
        with self.assertRaises(ValueError):
            DemandConfig(growth_min_periods=2)

    def test_pipeline_imports_without_site_packages(self):
        code = "from backend.domain.services.demand_preparation import prepare_demand"
        result = subprocess.run([sys.executable, "-B", "-S", "-c", code],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
