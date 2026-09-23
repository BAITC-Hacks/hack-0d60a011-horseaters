from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from backend.domain.entities.catalog import SupplierProduct
from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.entities.recommendation import Recommendation
from backend.domain.services.explanation import (
    build_calculation_details,
    build_explanation,
)
from backend.domain.services.replenishment import calculate_replenishment
from backend.domain.services.risk import RiskPolicy, assess_shortage_risk


def build_recommendation(
    *,
    forecast: DemandForecast,
    supplier_terms: SupplierProduct,
    current_stock: Decimal,
    in_transit_quantity: Decimal,
    material_requirement_quantity: Decimal,
    safety_stock: Decimal,
    planning_horizon_days: int,
    as_of: datetime,
    risk_policy: RiskPolicy | None = None,
    recommendation_id: UUID | None = None,
) -> Recommendation:
    """Compose ALG-06..09 outputs into the immutable calculated recommendation."""
    if supplier_terms.product_id != forecast.product_id:
        raise ValueError("supplier terms belong to another product")
    forecast_period_days = (forecast.period_end - forecast.period_start).days + 1
    replenishment = calculate_replenishment(
        forecast_quantity=forecast.forecast_quantity,
        forecast_period_days=forecast_period_days,
        planning_horizon_days=planning_horizon_days,
        lead_time_days=supplier_terms.lead_time_days,
        safety_stock=safety_stock,
        current_stock=current_stock,
        in_transit_quantity=in_transit_quantity,
        material_requirement_quantity=material_requirement_quantity,
        moq=supplier_terms.moq,
        package_size=supplier_terms.package_size,
    )
    daily_demand = forecast.forecast_quantity / Decimal(forecast_period_days)
    risk = assess_shortage_risk(
        as_of=as_of,
        daily_demand=daily_demand,
        demand_during_horizon=replenishment.demand_during_horizon,
        current_stock=current_stock,
        in_transit_quantity=in_transit_quantity,
        material_requirement_quantity=material_requirement_quantity,
        safety_stock=safety_stock,
        lead_time_days=supplier_terms.lead_time_days,
        policy=risk_policy,
    )
    details = build_calculation_details(
        forecast=forecast,
        replenishment=replenishment,
        risk=risk,
        current_stock=current_stock,
        in_transit_quantity=in_transit_quantity,
        material_requirement_quantity=material_requirement_quantity,
        safety_stock=safety_stock,
        moq=supplier_terms.moq,
        package_size=supplier_terms.package_size,
        lead_time_days=supplier_terms.lead_time_days,
    )
    values = dict(
        calculation_run_id=forecast.calculation_run_id,
        product_id=forecast.product_id,
        warehouse_id=forecast.warehouse_id,
        supplier_id=supplier_terms.supplier_id,
        forecast_quantity=forecast.forecast_quantity,
        current_stock=current_stock,
        in_transit_quantity=in_transit_quantity,
        material_requirement_quantity=material_requirement_quantity,
        safety_stock=safety_stock,
        shortage_quantity=replenishment.shortage_quantity,
        quantity_before_rounding=replenishment.quantity_before_rounding,
        moq=supplier_terms.moq,
        package_size=supplier_terms.package_size,
        recommended_quantity=replenishment.recommended_quantity,
        effective_quantity=replenishment.recommended_quantity,
        risk_score=risk.risk_score,
        urgency=risk.urgency,
        explanation=build_explanation(details),
        calculation_details=details,
    )
    if recommendation_id is not None:
        values["id"] = recommendation_id
    return Recommendation(**values)
