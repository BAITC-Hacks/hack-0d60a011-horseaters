from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.services.replenishment import ReplenishmentResult
from backend.domain.services.risk import RiskAssessment


def build_calculation_details(
    *,
    forecast: DemandForecast,
    replenishment: ReplenishmentResult,
    risk: RiskAssessment,
    current_stock: Decimal,
    in_transit_quantity: Decimal,
    material_requirement_quantity: Decimal,
    safety_stock: Decimal,
    moq: Decimal,
    package_size: Decimal,
    lead_time_days: int,
) -> dict[str, Any]:
    return {
        "baseline": forecast.cleaned_baseline,
        "raw_demand": forecast.raw_demand,
        "return_adjustment": forecast.return_adjustment,
        "anomaly_adjustment": forecast.anomaly_adjustment,
        "stockout_compensation": forecast.stockout_adjustment,
        "growth_rate": forecast.growth_rate,
        "growth_multiplier": Decimal("1") + forecast.growth_rate,
        "seasonality_index": forecast.seasonality_index,
        "forecast": forecast.forecast_quantity,
        "demand_during_horizon": replenishment.demand_during_horizon,
        "coverage_days": replenishment.coverage_days,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
        "current_stock": current_stock,
        "in_transit": in_transit_quantity,
        "material_requirements": material_requirement_quantity,
        "available_supply": replenishment.available_supply,
        "shortage_quantity": replenishment.shortage_quantity,
        "quantity_before_rounding": replenishment.quantity_before_rounding,
        "moq": moq,
        "package_size": package_size,
        "quantity_after_rounding": replenishment.recommended_quantity,
        "risk_score": risk.risk_score,
        "urgency": risk.urgency.value,
        "shortage_ratio": risk.shortage_ratio,
        "lead_time_gap_ratio": risk.lead_time_gap_ratio,
        "expected_stockout_at": _iso(risk.expected_stockout_at),
    }


def build_explanation(details: dict[str, Any]) -> str:
    return (
        f"Базовый спрос {details['baseline']}; после роста "
        f"{details['growth_multiplier']} и сезонности {details['seasonality_index']} "
        f"прогноз равен {details['forecast']}. На горизонт "
        f"{details['coverage_days']} дн. требуется {details['demand_during_horizon']}, "
        f"страховой запас {details['safety_stock']}, материальная потребность "
        f"{details['material_requirements']}; доступно на складе и в пути "
        f"{details['available_supply']}. До округления {details['quantity_before_rounding']}, "
        f"после MOQ {details['moq']} и кратности {details['package_size']} — "
        f"{details['quantity_after_rounding']}. Риск {details['risk_score']} "
        f"({details['urgency']})."
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
