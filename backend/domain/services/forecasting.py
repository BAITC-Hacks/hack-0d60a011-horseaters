from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from backend.domain.entities._validation import decimal_value
from backend.domain.entities.demand_forecast import DemandForecast


def calculate_demand_forecast(
    *,
    calculation_run_id: UUID,
    product_id: UUID,
    warehouse_id: UUID,
    period_start: date,
    period_end: date,
    raw_demand: Decimal,
    return_adjustment: Decimal = Decimal("0"),
    anomaly_adjustment: Decimal = Decimal("0"),
    stockout_adjustment: Decimal = Decimal("0"),
    growth_rate: Decimal = Decimal("0"),
    seasonality_index: Decimal = Decimal("1"),
    extra_details: dict[str, Any] | None = None,
) -> DemandForecast:
    """ALG-07: build a reproducible forecast from already measured adjustments."""
    values = {
        "raw_demand": raw_demand,
        "return_adjustment": return_adjustment,
        "anomaly_adjustment": anomaly_adjustment,
        "stockout_adjustment": stockout_adjustment,
        "growth_rate": growth_rate,
        "seasonality_index": seasonality_index,
    }
    for name, value in values.items():
        decimal_value(value, name)
    if raw_demand < 0:
        raise ValueError("raw_demand must be nonnegative")
    if return_adjustment > 0:
        raise ValueError("return_adjustment must be zero or negative")
    if stockout_adjustment < 0:
        raise ValueError("stockout_adjustment must be nonnegative")
    if growth_rate <= Decimal("-1"):
        raise ValueError("growth_rate must be greater than -1")
    if seasonality_index <= 0:
        raise ValueError("seasonality_index must be positive")

    cleaned_baseline = max(
        Decimal("0"),
        raw_demand + return_adjustment + anomaly_adjustment + stockout_adjustment,
    )
    growth_multiplier = Decimal("1") + growth_rate
    forecast_quantity = cleaned_baseline * growth_multiplier * seasonality_index
    details: dict[str, Any] = {
        "formula": "cleaned_baseline * (1 + growth_rate) * seasonality_index",
        "raw_demand": raw_demand,
        "return_adjustment": return_adjustment,
        "anomaly_adjustment": anomaly_adjustment,
        "stockout_adjustment": stockout_adjustment,
        "cleaned_baseline": cleaned_baseline,
        "growth_rate": growth_rate,
        "growth_multiplier": growth_multiplier,
        "seasonality_index": seasonality_index,
        "forecast_quantity": forecast_quantity,
    }
    if extra_details:
        details.update(extra_details)
    return DemandForecast(
        calculation_run_id=calculation_run_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        period_start=period_start,
        period_end=period_end,
        raw_demand=raw_demand,
        return_adjustment=return_adjustment,
        anomaly_adjustment=anomaly_adjustment,
        stockout_adjustment=stockout_adjustment,
        cleaned_baseline=cleaned_baseline,
        growth_rate=growth_rate,
        seasonality_index=seasonality_index,
        forecast_quantity=forecast_quantity,
        details=details,
    )
