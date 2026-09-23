from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from statistics import median

from backend.application.ports.unit_of_work import UnitOfWork
from backend.domain.entities.calculation_run import CalculationRun
from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.entities.detected_anomaly import DetectedAnomaly
from backend.domain.entities.recommendation import Recommendation
from backend.domain.services.forecasting import calculate_demand_forecast
from backend.domain.services.recommendation import build_recommendation
from backend.domain.value_objects.demand import DemandSource


@dataclass(frozen=True, slots=True)
class CalculationResults:
    anomalies: list[DetectedAnomaly]
    forecasts: list[DemandForecast]
    recommendations: list[Recommendation]


def _quartile(values: list[Decimal], fraction: Decimal) -> Decimal:
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _stockout_days(periods, start, end) -> int:
    """Count the union of half-open stockout intervals, clipped to history."""
    intervals = sorted(
        (max(item.started_at, start), min(item.ended_at or end, end))
        for item in periods
        if max(item.started_at, start) < min(item.ended_at or end, end)
    )
    merged = []
    for left, right in intervals:
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return min(365, sum((right - left).days for left, right in merged))


class CalculationPipeline:
    """Build one 30-day forecast per SKU/warehouse from a fixed import snapshot."""

    def calculate(self, run: CalculationRun, uow: UnitOfWork) -> CalculationResults:
        start = run.source_cutoff_at - timedelta(days=365)
        end = run.source_cutoff_at
        batch_ids = run.import_batch_ids
        demand_source = DemandSource(run.parameters["demand_source"])
        products = uow.products.list_products(category_id=run.category_id) if run.category_id else uow.products.list_products()
        warehouses = [run.warehouse_id] if run.warehouse_id else uow.warehouses.list_active_ids()
        anomalies: list[DetectedAnomaly] = []
        forecasts: list[DemandForecast] = []
        recommendations: list[Recommendation] = []
        forecast_start = end.date()
        forecast_end = forecast_start + timedelta(days=29)

        for product in products:
            terms = sorted(
                uow.suppliers.list_terms(product.id),
                key=lambda item: (not item.is_primary, item.priority, item.lead_time_days, str(item.supplier_id)),
            )
            for warehouse_id in warehouses:
                transactions = uow.sales.list_transactions(
                    start, end, product_id=product.id, warehouse_id=warehouse_id,
                    import_batch_ids=batch_ids,
                ) if demand_source is DemandSource.TRANSACTIONS else []
                sales = [item for item in transactions if item.quantity > 0]
                returns = [item for item in transactions if item.quantity < 0]
                raw_total = sum((item.quantity for item in sales), Decimal("0"))
                return_total = sum((item.quantity for item in returns), Decimal("0"))
                anomaly_total = Decimal("0")
                if len(sales) >= 4:
                    quantities = [item.quantity for item in sales]
                    q1 = _quartile(quantities, Decimal("0.25"))
                    q3 = _quartile(quantities, Decimal("0.75"))
                    threshold = q3 + Decimal("1.5") * (q3 - q1)
                    replacement = Decimal(str(median(quantities)))
                    for item in sales:
                        if item.quantity > threshold:
                            anomaly_total += replacement - item.quantity
                            anomalies.append(DetectedAnomaly(
                                calculation_run_id=run.id,
                                sales_transaction_id=item.id, method="iqr",
                                original_quantity=item.quantity,
                                replacement_quantity=replacement,
                                threshold=threshold,
                                reason="Разовая крупная отгрузка исключена из регулярного спроса",
                            ))
                monthly_source = demand_source is DemandSource.MONTHLY_SALES
                if monthly_source:
                    monthly = uow.sales.list_monthly_sales(
                        start.date(), (end - timedelta(days=1)).date(),
                        product_id=product.id, warehouse_id=warehouse_id,
                        import_batch_ids=batch_ids,
                    )
                    if monthly:
                        raw_total = sum((max(Decimal("0"), item.quantity) for item in monthly), Decimal("0"))
                        return_total = sum((min(Decimal("0"), item.quantity) for item in monthly), Decimal("0"))
                if raw_total == 0 and return_total == 0:
                    continue

                stockouts = uow.inventory.list_stockout_periods(
                    start, end, product_id=product.id, warehouse_id=warehouse_id,
                    import_batch_ids=batch_ids,
                )
                stockout_days = _stockout_days(stockouts, start, end)
                observed_days = max(1, 365 - stockout_days)
                regular_total = max(Decimal("0"), raw_total + return_total + anomaly_total)
                stockout_total = regular_total * Decimal(stockout_days) / Decimal(observed_days)
                scale = Decimal("30") / Decimal("365")

                coefficient = uow.seasonality.get_coefficient(
                    product.id, forecast_start, import_batch_ids=batch_ids
                )
                seasonality_index = coefficient.coefficient if coefficient else Decimal("1")
                assumptions = uow.seasonality.list_growth_assumptions(
                    forecast_start, import_batch_ids=batch_ids
                )
                matching = [item for item in assumptions
                            if (item.product_id == product.id or
                                (item.product_id is None and item.category_id == product.category_id))
                            and (item.warehouse_id is None or item.warehouse_id == warehouse_id)]
                matching.sort(key=lambda item: (
                    item.product_id != product.id, item.warehouse_id != warehouse_id,
                    -item.valid_from.toordinal(), str(item.id),
                ))
                growth_rate = matching[0].growth_rate if matching else Decimal("0")
                forecast = calculate_demand_forecast(
                    calculation_run_id=run.id, product_id=product.id,
                    warehouse_id=warehouse_id, period_start=forecast_start,
                    period_end=forecast_end, raw_demand=raw_total * scale,
                    return_adjustment=return_total * scale,
                    anomaly_adjustment=anomaly_total * scale,
                    stockout_adjustment=stockout_total * scale,
                    growth_rate=growth_rate, seasonality_index=seasonality_index,
                    extra_details={
                        "historical_days": 365, "stockout_days": stockout_days,
                        "source": "monthly_sales" if monthly_source else "sales_transactions",
                        "import_batch_ids": [str(item) for item in sorted(batch_ids)],
                    },
                )
                forecasts.append(forecast)
                if not terms:
                    raise ValueError(f"active supplier terms missing for product {product.id}")
                snapshot = uow.inventory.get_latest_snapshot(
                    product.id, warehouse_id, end, import_batch_ids=batch_ids
                )
                stock = max(Decimal("0"), snapshot.quantity_available) if snapshot else Decimal("0")
                transit = sum((item.quantity for item in uow.inventory.list_active_in_transit(
                    product_id=product.id, warehouse_id=warehouse_id,
                    expected_from=end, expected_before=end + timedelta(days=run.forecast_horizon_days),
                    import_batch_ids=batch_ids,
                )), Decimal("0"))
                material = sum((item.required_quantity for item in uow.material_requirements.list_requirements(
                    end, end + timedelta(days=run.forecast_horizon_days),
                    product_id=product.id, warehouse_id=warehouse_id,
                    import_batch_ids=batch_ids,
                )), Decimal("0"))
                safety = forecast.forecast_quantity * Decimal("7") / Decimal("30")
                recommendations.append(build_recommendation(
                    forecast=forecast, supplier_terms=terms[0], current_stock=stock,
                    in_transit_quantity=transit,
                    material_requirement_quantity=material, safety_stock=safety,
                    planning_horizon_days=run.forecast_horizon_days, as_of=end,
                ))
        return CalculationResults(anomalies, forecasts, recommendations)
