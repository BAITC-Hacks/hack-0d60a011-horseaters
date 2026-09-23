"""Inputs and explainable results of demand preparation, independent of persistence."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from backend.domain.entities.detected_anomaly import DetectedAnomaly
from backend.domain.entities.imports import StockoutPeriod
from backend.domain.entities.product import Product
from backend.domain.enums import GrowthSource


class DemandSource(str, Enum):
    TRANSACTIONS = "transactions"
    MONTHLY_SALES = "monthly_sales"


@dataclass(frozen=True, kw_only=True)
class DemandConfig:
    iqr_multiplier: Decimal = Decimal("1.5")
    anomaly_min_samples: int = 4
    zero_iqr_multiplier: Decimal = Decimal("3")
    stockout_min_snapshots: int = 3
    stockout_max_snapshot_gap_days: int = 45
    stockout_min_baseline_periods: int = 2
    stockout_baseline_neighbors: int = 4
    growth_window_months: int = 3
    growth_min_periods: int = 6
    growth_min_factor: Decimal = Decimal("0.5")
    growth_max_factor: Decimal = Decimal("2")

    def __post_init__(self) -> None:
        for name in ("iqr_multiplier", "zero_iqr_multiplier", "growth_min_factor", "growth_max_factor"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise ValueError(f"{name} must be a finite positive Decimal")
        for name in ("anomaly_min_samples", "stockout_min_snapshots", "stockout_max_snapshot_gap_days",
                     "stockout_min_baseline_periods", "stockout_baseline_neighbors",
                     "growth_window_months", "growth_min_periods"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.anomaly_min_samples < 4 or self.zero_iqr_multiplier <= 1:
            raise ValueError("Anomaly detection needs >= 4 samples and zero_iqr_multiplier > 1")
        if self.stockout_min_snapshots < 3 or self.stockout_min_baseline_periods < 2:
            raise ValueError("Stockout needs >= 3 snapshots and >= 2 baseline periods")
        if self.stockout_baseline_neighbors < self.stockout_min_baseline_periods:
            raise ValueError("Not enough stockout baseline neighbors")
        if self.growth_window_months < 2 or self.growth_min_periods < 2 * self.growth_window_months:
            raise ValueError("Growth needs two windows of at least two months")
        if not self.growth_min_factor <= 1 <= self.growth_max_factor:
            raise ValueError("Growth bounds must include the neutral factor 1")


@dataclass(frozen=True, kw_only=True)
class DemandGroup:
    product: Product
    warehouse_id: UUID | None

    @property
    def key(self) -> tuple[UUID, UUID | None]:
        return self.product.id, self.warehouse_id


@dataclass(frozen=True, kw_only=True)
class PeriodAnomaly:
    """Monthly aggregate audit; cannot be persisted as a transaction anomaly."""
    period_start: date
    period_end: date
    source_row_ids: tuple[UUID, ...]
    original_quantity: Decimal
    replacement_quantity: Decimal
    threshold: Decimal
    method: str = "monthly_iqr"


@dataclass(frozen=True, kw_only=True)
class GrowthEstimate:
    factor: Decimal
    unclamped_factor: Decimal
    source: GrowthSource
    reason: str
    assumption_id: UUID | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class PreparedDemandPeriod:
    period_start: date
    period_end: date
    raw_demand: Decimal
    return_adjustment: Decimal
    demand_after_returns: Decimal
    anomaly_adjustment: Decimal
    nonnegative_adjustment: Decimal
    stockout_adjustment: Decimal
    cleaned_demand: Decimal
    growth_adjustment: Decimal
    calculated_demand: Decimal
    observed: bool
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class PreparedDemandSeries:
    product_id: UUID
    sku: str
    warehouse_id: UUID | None
    unit: str
    source: DemandSource
    periods: tuple[PreparedDemandPeriod, ...]
    growth: GrowthEstimate
    anomalies: tuple[DetectedAnomaly, ...]
    period_anomalies: tuple[PeriodAnomaly, ...]
    stockout_periods: tuple[StockoutPeriod, ...]
    customer_check: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class DemandPreparationResult:
    calculation_run_id: UUID
    source: DemandSource
    period_start: date
    period_end: date
    source_cutoff_at: datetime
    series: tuple[PreparedDemandSeries, ...]
    parameters: Mapping[str, Any]
