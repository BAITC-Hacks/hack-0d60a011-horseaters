from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DemandForecast:
    calculation_run_id: UUID
    product_id: UUID
    warehouse_id: UUID
    period_start: date
    period_end: date
    raw_demand: Decimal
    return_adjustment: Decimal
    anomaly_adjustment: Decimal
    stockout_adjustment: Decimal
    cleaned_baseline: Decimal
    growth_rate: Decimal
    seasonality_index: Decimal
    forecast_quantity: Decimal
    details: Mapping[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be earlier than period_start")
        if self.raw_demand < 0:
            raise ValueError("raw_demand must be nonnegative")
        if self.return_adjustment > 0:
            raise ValueError("return_adjustment must be zero or negative")
        if self.stockout_adjustment < 0:
            raise ValueError("stockout_adjustment must be nonnegative")
        if self.cleaned_baseline < 0:
            raise ValueError("cleaned_baseline must be nonnegative")
        if self.growth_rate <= Decimal("-1"):
            raise ValueError("growth_rate must be greater than -1")
        if self.seasonality_index <= 0:
            raise ValueError("seasonality_index must be positive")
        if self.forecast_quantity < 0:
            raise ValueError("forecast_quantity must be nonnegative")
