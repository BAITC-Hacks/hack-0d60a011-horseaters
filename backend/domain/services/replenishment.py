from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from backend.domain.entities._validation import decimal_value, positive_decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplenishmentResult:
    demand_during_horizon: Decimal
    coverage_days: int
    available_supply: Decimal
    shortage_quantity: Decimal
    quantity_before_rounding: Decimal
    recommended_quantity: Decimal


def calculate_replenishment(
    *,
    forecast_quantity: Decimal,
    forecast_period_days: int,
    planning_horizon_days: int,
    lead_time_days: int,
    safety_stock: Decimal,
    current_stock: Decimal,
    in_transit_quantity: Decimal,
    material_requirement_quantity: Decimal,
    moq: Decimal,
    package_size: Decimal,
) -> ReplenishmentResult:
    """ALG-08: calculate net requirement and round it to supplier constraints."""
    nonnegative = {
        "forecast_quantity": forecast_quantity,
        "safety_stock": safety_stock,
        "current_stock": current_stock,
        "in_transit_quantity": in_transit_quantity,
        "material_requirement_quantity": material_requirement_quantity,
    }
    for name, value in nonnegative.items():
        decimal_value(value, name, minimum=Decimal("0"))
    positive_decimal(moq, "moq")
    positive_decimal(package_size, "package_size")
    if forecast_period_days <= 0:
        raise ValueError("forecast_period_days must be positive")
    if planning_horizon_days <= 0:
        raise ValueError("planning_horizon_days must be positive")
    if lead_time_days < 0:
        raise ValueError("lead_time_days must be nonnegative")

    coverage_days = planning_horizon_days + lead_time_days
    daily_demand = forecast_quantity / Decimal(forecast_period_days)
    demand_during_horizon = daily_demand * Decimal(coverage_days)
    available_supply = current_stock + in_transit_quantity
    shortage_quantity = max(
        Decimal("0"),
        demand_during_horizon + material_requirement_quantity - available_supply,
    )
    quantity_before_rounding = max(
        Decimal("0"),
        demand_during_horizon
        + safety_stock
        + material_requirement_quantity
        - available_supply,
    )
    recommended_quantity = round_to_supplier_constraints(
        quantity_before_rounding,
        moq=moq,
        package_size=package_size,
    )
    return ReplenishmentResult(
        demand_during_horizon=demand_during_horizon,
        coverage_days=coverage_days,
        available_supply=available_supply,
        shortage_quantity=shortage_quantity,
        quantity_before_rounding=quantity_before_rounding,
        recommended_quantity=recommended_quantity,
    )


def round_to_supplier_constraints(
    quantity: Decimal,
    *,
    moq: Decimal,
    package_size: Decimal,
) -> Decimal:
    decimal_value(quantity, "quantity", minimum=Decimal("0"))
    positive_decimal(moq, "moq")
    positive_decimal(package_size, "package_size")
    if quantity == 0:
        return Decimal("0")
    target = max(quantity, moq)
    packages = (target / package_size).to_integral_value(rounding=ROUND_CEILING)
    return packages * package_size
