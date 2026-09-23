import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from backend.domain.entities.catalog import SupplierProduct
from backend.domain.entities.imports import SeasonalityCoefficient
from backend.domain.entities.enums import Urgency
from backend.domain.services import (
    AmbiguousSeasonalityError,
    RiskPolicy,
    assess_shortage_risk,
    build_recommendation,
    calculate_demand_forecast,
    calculate_replenishment,
    round_to_supplier_constraints,
    select_seasonality_index,
    urgency_for_score,
)


class Alg0609Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = uuid4()
        self.product_id = uuid4()
        self.category_id = uuid4()
        self.warehouse_id = uuid4()
        self.supplier_id = uuid4()
        self.import_id = uuid4()
        self.as_of = datetime(2026, 9, 23, tzinfo=timezone.utc)

    def coefficient(self, **changes) -> SeasonalityCoefficient:
        values = dict(
            import_batch_id=self.import_id,
            product_id=self.product_id,
            month=9,
            coefficient=Decimal("1.20"),
            valid_from=date(2026, 1, 1),
            version=1,
        )
        values.update(changes)
        return SeasonalityCoefficient(**values)

    def forecast(self, **changes):
        values = dict(
            calculation_run_id=self.run_id,
            product_id=self.product_id,
            warehouse_id=self.warehouse_id,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
            raw_demand=Decimal("100"),
            return_adjustment=Decimal("-10"),
            anomaly_adjustment=Decimal("-20"),
            stockout_adjustment=Decimal("15"),
            growth_rate=Decimal("0.10"),
            seasonality_index=Decimal("1.20"),
        )
        values.update(changes)
        return calculate_demand_forecast(**values)

    def terms(self, **changes) -> SupplierProduct:
        values = dict(
            supplier_id=self.supplier_id,
            product_id=self.product_id,
            moq=Decimal("40"),
            package_size=Decimal("12"),
            lead_time_days=10,
        )
        values.update(changes)
        return SupplierProduct(**values)

    def test_alg_06_product_seasonality_overrides_category_and_defaults_to_one(self):
        category = self.coefficient(
            product_id=None,
            category_id=self.category_id,
            coefficient=Decimal("0.80"),
        )
        product = self.coefficient(coefficient=Decimal("1.35"))
        selected = select_seasonality_index(
            [category, product],
            product_id=self.product_id,
            category_id=self.category_id,
            on_date=date(2026, 9, 15),
        )
        self.assertEqual(selected, Decimal("1.35"))
        self.assertEqual(
            select_seasonality_index(
                [],
                product_id=self.product_id,
                category_id=self.category_id,
                on_date=date(2026, 9, 15),
            ),
            Decimal("1"),
        )

    def test_alg_06_requires_version_when_active_coefficients_are_ambiguous(self):
        first = self.coefficient(version=1)
        second = self.coefficient(version=2, coefficient=Decimal("1.40"))
        with self.assertRaises(AmbiguousSeasonalityError):
            select_seasonality_index(
                [first, second],
                product_id=self.product_id,
                category_id=self.category_id,
                on_date=date(2026, 9, 15),
            )
        self.assertEqual(
            select_seasonality_index(
                [first, second],
                product_id=self.product_id,
                category_id=self.category_id,
                on_date=date(2026, 9, 15),
                version=2,
            ),
            Decimal("1.40"),
        )

    def test_alg_07_forecast_uses_every_adjustment_growth_and_seasonality(self):
        forecast = self.forecast()
        self.assertEqual(forecast.cleaned_baseline, Decimal("85"))
        self.assertEqual(forecast.forecast_quantity, Decimal("112.2000"))
        self.assertEqual(forecast.details["growth_multiplier"], Decimal("1.10"))
        self.assertEqual(forecast.details["seasonality_index"], Decimal("1.20"))

        without_stockout = self.forecast(stockout_adjustment=Decimal("0"))
        without_growth = self.forecast(growth_rate=Decimal("0"))
        without_seasonality = self.forecast(seasonality_index=Decimal("1"))
        self.assertLess(without_stockout.forecast_quantity, forecast.forecast_quantity)
        self.assertLess(without_growth.forecast_quantity, forecast.forecast_quantity)
        self.assertLess(without_seasonality.forecast_quantity, forecast.forecast_quantity)

    def test_alg_08_horizon_includes_lead_time_and_rounds_moq_and_package(self):
        result = calculate_replenishment(
            forecast_quantity=Decimal("30"),
            forecast_period_days=30,
            planning_horizon_days=30,
            lead_time_days=10,
            safety_stock=Decimal("10"),
            current_stock=Decimal("20"),
            in_transit_quantity=Decimal("5"),
            material_requirement_quantity=Decimal("5"),
            moq=Decimal("40"),
            package_size=Decimal("12"),
        )
        self.assertEqual(result.coverage_days, 40)
        self.assertEqual(result.demand_during_horizon, Decimal("40"))
        self.assertEqual(result.quantity_before_rounding, Decimal("30"))
        self.assertEqual(result.recommended_quantity, Decimal("48"))
        self.assertEqual(
            round_to_supplier_constraints(
                Decimal("0"), moq=Decimal("40"), package_size=Decimal("12")
            ),
            Decimal("0"),
        )

    def test_alg_09_risk_is_critical_for_no_stock_and_low_for_ample_stock(self):
        critical = assess_shortage_risk(
            as_of=self.as_of,
            daily_demand=Decimal("10"),
            demand_during_horizon=Decimal("100"),
            current_stock=Decimal("0"),
            in_transit_quantity=Decimal("0"),
            material_requirement_quantity=Decimal("0"),
            safety_stock=Decimal("10"),
            lead_time_days=7,
        )
        low = assess_shortage_risk(
            as_of=self.as_of,
            daily_demand=Decimal("10"),
            demand_during_horizon=Decimal("100"),
            current_stock=Decimal("200"),
            in_transit_quantity=Decimal("0"),
            material_requirement_quantity=Decimal("0"),
            safety_stock=Decimal("10"),
            lead_time_days=7,
        )
        self.assertEqual(critical.risk_score, Decimal("1.00"))
        self.assertEqual(critical.urgency, Urgency.CRITICAL)
        self.assertEqual(low.risk_score, Decimal("0.00"))
        self.assertEqual(low.urgency, Urgency.LOW)

    def test_risk_thresholds_are_configurable_and_validated(self):
        policy = RiskPolicy(
            medium_threshold=Decimal("0.10"),
            high_threshold=Decimal("0.20"),
            critical_threshold=Decimal("0.30"),
        )
        self.assertEqual(urgency_for_score(Decimal("0.25"), policy), Urgency.HIGH)
        with self.assertRaisesRegex(ValueError, "increasing"):
            RiskPolicy(
                medium_threshold=Decimal("0.5"),
                high_threshold=Decimal("0.4"),
                critical_threshold=Decimal("0.9"),
            )

    def test_end_to_end_recommendation_contains_explanation_and_breakdown(self):
        recommendation = build_recommendation(
            forecast=self.forecast(),
            supplier_terms=self.terms(),
            current_stock=Decimal("20"),
            in_transit_quantity=Decimal("5"),
            material_requirement_quantity=Decimal("5"),
            safety_stock=Decimal("10"),
            planning_horizon_days=30,
            as_of=self.as_of,
        )
        self.assertGreater(recommendation.recommended_quantity, 0)
        self.assertEqual(
            recommendation.effective_quantity,
            recommendation.recommended_quantity,
        )
        self.assertIn("MOQ", recommendation.explanation)
        expected_keys = {
            "baseline", "return_adjustment", "anomaly_adjustment",
            "stockout_compensation", "growth_multiplier", "seasonality_index",
            "forecast", "safety_stock", "current_stock", "in_transit",
            "material_requirements", "quantity_before_rounding", "moq",
            "package_size", "quantity_after_rounding", "risk_score", "urgency",
        }
        self.assertTrue(expected_keys.issubset(recommendation.calculation_details))

        more_transit = build_recommendation(
            forecast=self.forecast(),
            supplier_terms=self.terms(),
            current_stock=Decimal("20"),
            in_transit_quantity=Decimal("500"),
            material_requirement_quantity=Decimal("5"),
            safety_stock=Decimal("10"),
            planning_horizon_days=30,
            as_of=self.as_of,
        )
        self.assertEqual(more_transit.recommended_quantity, Decimal("0"))
        self.assertLess(more_transit.risk_score, recommendation.risk_score)

    def test_recommendation_rejects_terms_for_another_product(self):
        with self.assertRaisesRegex(ValueError, "another product"):
            build_recommendation(
                forecast=self.forecast(),
                supplier_terms=replace(self.terms(), product_id=uuid4()),
                current_stock=Decimal("0"),
                in_transit_quantity=Decimal("0"),
                material_requirement_quantity=Decimal("0"),
                safety_stock=Decimal("0"),
                planning_horizon_days=30,
                as_of=self.as_of,
            )


if __name__ == "__main__":
    unittest.main()
