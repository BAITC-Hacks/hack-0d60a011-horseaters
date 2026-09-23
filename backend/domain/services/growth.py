"""A bounded, explained comparison of two adjacent windows of cleaned demand."""

from decimal import Decimal

from backend.domain.entities.imports import GrowthAssumption
from backend.domain.enums import GrowthSource
from backend.domain.value_objects.demand import DemandConfig, GrowthEstimate
from ._demand_math import ONE, ZERO


def estimate_growth(
    daily_rates: list[Decimal], config: DemandConfig, override: GrowthAssumption | None = None,
) -> GrowthEstimate:
    details = {}
    if override is not None:
        original = ONE + override.growth_rate
        if not original.is_finite() or original <= 0:
            raise ValueError("Growth assumption must have growth_rate > -1")
        source, reason = override.source, "explicit_assumption"
    else:
        source, reason, original = GrowthSource.CALCULATED, "insufficient_history", ONE
        size = config.growth_window_months
        if len(daily_rates) >= config.growth_min_periods:
            previous = sum(daily_rates[-2 * size:-size], ZERO) / size
            recent = daily_rates[-size:]
            current = sum(recent, ZERO) / size
            details = {"previous_daily_mean": str(previous), "recent_daily_mean": str(current), "window_months": size}
            reason = "zero_baseline"
            if previous > 0:
                candidate = current / previous
                direction_count = sum(value > previous if candidate > 1 else value < previous for value in recent)
                # At least two thirds of the recent months must support the trend.
                if candidate != 1 and direction_count * 3 >= size * 2:
                    original, reason = candidate, "sustained_window_means"
                else:
                    reason = "no_sustained_change"
    factor = min(config.growth_max_factor, max(config.growth_min_factor, original))
    return GrowthEstimate(
        factor=factor, unclamped_factor=original, source=source, reason=reason,
        assumption_id=override.id if override else None,
        details={**details, "clamped": factor != original},
    )
