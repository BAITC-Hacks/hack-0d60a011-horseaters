from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR

from backend.domain.entities._validation import aware_datetime, decimal_value
from backend.domain.entities.enums import Urgency


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskPolicy:
    medium_threshold: Decimal = Decimal("0.35")
    high_threshold: Decimal = Decimal("0.65")
    critical_threshold: Decimal = Decimal("0.85")

    def __post_init__(self) -> None:
        thresholds = (
            self.medium_threshold,
            self.high_threshold,
            self.critical_threshold,
        )
        for value in thresholds:
            decimal_value(value, "risk threshold", minimum=Decimal("0"))
            if value > 1:
                raise ValueError("risk thresholds must not exceed 1")
        if not thresholds[0] < thresholds[1] < thresholds[2]:
            raise ValueError("risk thresholds must be strictly increasing")


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskAssessment:
    risk_score: Decimal
    urgency: Urgency
    shortage_ratio: Decimal
    lead_time_gap_ratio: Decimal
    expected_stockout_at: datetime | None


def assess_shortage_risk(
    *,
    as_of: datetime,
    daily_demand: Decimal,
    demand_during_horizon: Decimal,
    current_stock: Decimal,
    in_transit_quantity: Decimal,
    material_requirement_quantity: Decimal,
    safety_stock: Decimal,
    lead_time_days: int,
    policy: RiskPolicy | None = None,
) -> RiskAssessment:
    """ALG-09: score shortage severity and map it to an urgency level."""
    aware_datetime(as_of, "as_of")
    values = {
        "daily_demand": daily_demand,
        "demand_during_horizon": demand_during_horizon,
        "current_stock": current_stock,
        "in_transit_quantity": in_transit_quantity,
        "material_requirement_quantity": material_requirement_quantity,
        "safety_stock": safety_stock,
    }
    for name, value in values.items():
        decimal_value(value, name, minimum=Decimal("0"))
    if lead_time_days < 0:
        raise ValueError("lead_time_days must be nonnegative")
    selected_policy = policy or RiskPolicy()

    required = demand_during_horizon + material_requirement_quantity + safety_stock
    available = current_stock + in_transit_quantity
    shortage = max(Decimal("0"), required - available)
    shortage_ratio = Decimal("0") if required == 0 else shortage / required

    if daily_demand == 0:
        coverage_days = None
        lead_time_gap_ratio = Decimal("0")
        expected_stockout_at = None
    else:
        coverage = available / daily_demand
        coverage_days = int(coverage.to_integral_value(rounding=ROUND_FLOOR))
        expected_stockout_at = as_of + timedelta(days=max(coverage_days, 0))
        lead_time_gap = max(Decimal("0"), Decimal(lead_time_days) - coverage)
        lead_time_gap_ratio = lead_time_gap / Decimal(max(lead_time_days, 1))
        lead_time_gap_ratio = min(Decimal("1"), lead_time_gap_ratio)

    score = min(
        Decimal("1"),
        max(
            Decimal("0"),
            Decimal("0.70") * shortage_ratio
            + Decimal("0.30") * lead_time_gap_ratio,
        ),
    )
    urgency = urgency_for_score(score, selected_policy)
    return RiskAssessment(
        risk_score=score,
        urgency=urgency,
        shortage_ratio=shortage_ratio,
        lead_time_gap_ratio=lead_time_gap_ratio,
        expected_stockout_at=expected_stockout_at,
    )


def urgency_for_score(score: Decimal, policy: RiskPolicy | None = None) -> Urgency:
    decimal_value(score, "score", minimum=Decimal("0"))
    if score > 1:
        raise ValueError("score must not exceed 1")
    selected = policy or RiskPolicy()
    if score >= selected.critical_threshold:
        return Urgency.CRITICAL
    if score >= selected.high_threshold:
        return Urgency.HIGH
    if score >= selected.medium_threshold:
        return Urgency.MEDIUM
    return Urgency.LOW
