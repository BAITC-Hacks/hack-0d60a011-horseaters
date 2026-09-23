"""TEST-02: business-facing algorithm sensitivities on synthetic facts."""

import unittest
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from backend.domain.entities.imports import MonthlySales, SalesTransaction, StockoutPeriod
from backend.domain.entities.product import Product
from backend.domain.enums import StockoutSource, TransactionType
from backend.domain.services.demand_preparation import prepare_demand
from backend.domain.services.forecasting import calculate_demand_forecast
from backend.domain.services.replenishment import calculate_replenishment
from backend.domain.value_objects.demand import DemandGroup, DemandSource


D = Decimal


class AlgorithmAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.product = Product(sku="SKU-TEST", name="Synthetic product", unit="pcs")
        self.warehouse_id = uuid4()
        self.batch_id = uuid4()
        self.run_id = uuid4()
        self.row_number = 0

    def sale(self, month, quantity, *, customer=None, transaction_type=TransactionType.SALE):
        self.row_number += 1
        return SalesTransaction(
            import_batch_id=self.batch_id, source_row_number=self.row_number,
            sold_at=datetime(2026, month, 1, tzinfo=timezone.utc),
            product_id=self.product.id, warehouse_id=self.warehouse_id,
            transaction_type=transaction_type, quantity=D(quantity),
            anonymous_customer_id=customer,
        )

    def monthly(self, month, quantity):
        self.row_number += 1
        return MonthlySales(
            import_batch_id=self.batch_id, source_row_number=self.row_number,
            product_id=self.product.id, warehouse_id=self.warehouse_id,
            period_start=date(2026, month, 1),
            period_end=date(2026, month, monthrange(2026, month)[1]),
            quantity=D(quantity),
        )

    def prepare(self, *, source=DemandSource.TRANSACTIONS, transactions=(), monthly=(), stockouts=()):
        return prepare_demand(
            calculation_run_id=self.run_id, source=source,
            start=date(2026, 1, 1), end=date(2026, 6, 30),
            source_cutoff_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            groups=[DemandGroup(product=self.product, warehouse_id=self.warehouse_id)],
            transactions=transactions, monthly_sales=monthly, stockouts=stockouts,
        ).series[0]

    def replenishment(self, *, stock=D("0"), transit=D("0"), moq=D("1"), package=D("1")):
        return calculate_replenishment(
            forecast_quantity=D("30"), forecast_period_days=30,
            planning_horizon_days=30, lead_time_days=0,
            safety_stock=D("0"), current_stock=stock,
            in_transit_quantity=transit, material_requirement_quantity=D("0"),
            moq=moq, package_size=package,
        )

    def test_one_off_large_sale_does_not_increase_regular_demand(self):
        regular = [self.sale(month, "10") for month in range(1, 7)]
        typical = self.sale(5, "10")
        spike = self.sale(5, "100")
        baseline = self.prepare(transactions=[*regular, typical])
        with_spike = self.prepare(transactions=[*regular, spike])
        self.assertEqual(sum(period.cleaned_demand for period in baseline.periods),
                         sum(period.cleaned_demand for period in with_spike.periods))
        self.assertEqual(with_spike.anomalies[0].sales_transaction_id, spike.id)
        self.assertEqual(spike.quantity, D("100"))

    def test_large_sale_split_across_documents_for_one_customer_is_detected(self):
        customer = "anonymous-17"
        rows = [self.sale(month, "10", customer=customer) for month in range(1, 5)]
        rows += [self.sale(5, "10", customer=customer) for _ in range(10)]
        result = self.prepare(transactions=rows)
        self.assertEqual(result.periods[4].raw_demand, D("100"))
        self.assertEqual(result.periods[4].cleaned_demand, D("10"))
        self.assertEqual({item.method for item in result.anomalies}, {"customer_period_iqr"})

    def test_stockout_compensation_increases_prepared_demand(self):
        monthly = [self.monthly(1, "310"), self.monthly(2, "280")]
        outage = StockoutPeriod(
            product_id=self.product.id, warehouse_id=self.warehouse_id,
            started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ended_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            source=StockoutSource.IMPORTED,
        )
        raw = self.prepare(source=DemandSource.MONTHLY_SALES, monthly=monthly)
        adjusted = self.prepare(source=DemandSource.MONTHLY_SALES, monthly=monthly, stockouts=[outage])
        self.assertEqual(raw.periods[2].cleaned_demand, D("0"))
        self.assertGreater(adjusted.periods[2].cleaned_demand, raw.periods[2].cleaned_demand)
        self.assertEqual(adjusted.periods[2].stockout_adjustment, D("310"))

    def test_seasonality_changes_forecast(self):
        arguments = dict(
            calculation_run_id=self.run_id, product_id=self.product.id,
            warehouse_id=self.warehouse_id, period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30), raw_demand=D("100"),
        )
        neutral = calculate_demand_forecast(**arguments, seasonality_index=D("1"))
        seasonal = calculate_demand_forecast(**arguments, seasonality_index=D("1.4"))
        self.assertEqual((neutral.forecast_quantity, seasonal.forecast_quantity), (D("100"), D("140")))

    def test_sustained_growth_increases_regular_demand(self):
        rows = [self.monthly(month, D(days) * D(rate)) for month, days, rate in
                ((1, 31, 10), (2, 28, 10), (3, 31, 10),
                 (4, 30, 30), (5, 31, 30), (6, 30, 30))]
        result = self.prepare(source=DemandSource.MONTHLY_SALES, monthly=rows)
        self.assertGreater(result.growth.factor, D("1"))
        self.assertGreater(result.periods[-1].calculated_demand, result.periods[-1].cleaned_demand)

    def test_in_transit_reduces_order(self):
        without = self.replenishment(transit=D("0"))
        with_transit = self.replenishment(transit=D("20"))
        self.assertEqual((without.recommended_quantity, with_transit.recommended_quantity), (D("30"), D("10")))

    def test_moq_and_package_round_order_up(self):
        result = self.replenishment(stock=D("23"), moq=D("12"), package=D("5"))
        self.assertEqual(result.quantity_before_rounding, D("7"))
        self.assertEqual(result.recommended_quantity, D("15"))

    def test_stock_change_alters_order(self):
        empty = self.replenishment(stock=D("0"))
        stocked = self.replenishment(stock=D("10"))
        self.assertEqual((empty.recommended_quantity, stocked.recommended_quantity), (D("30"), D("20")))

    def test_return_reduces_demand_without_mutating_sale(self):
        sale = self.sale(1, "20")
        returned = self.sale(1, "-5", transaction_type=TransactionType.RETURN)
        before = self.prepare(transactions=[sale])
        after = self.prepare(transactions=[sale, returned])
        self.assertEqual((before.periods[0].cleaned_demand, after.periods[0].cleaned_demand),
                         (D("20"), D("15")))
        self.assertEqual((sale.quantity, returned.quantity), (D("20"), D("-5")))


if __name__ == "__main__":
    unittest.main()
