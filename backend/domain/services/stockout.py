"""Conservative stockout evidence and compensation; never edits source facts."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from backend.domain.entities.imports import InventorySnapshot, StockoutPeriod
from backend.domain.enums import StockoutSource
from backend.domain.repositories.filters import AmbiguousSourceDataError
from backend.domain.value_objects.demand import DemandConfig
from ._demand_math import ZERO, days, median, midnight, utc


def compensate_stockout(
    periods: tuple[tuple[date, date], ...], cleaned: list[Decimal], observed: list[bool],
    stockouts: list[StockoutPeriod], snapshots: list[InventorySnapshot],
    run_id: UUID, config: DemandConfig,
) -> tuple[list[Decimal], list[dict], tuple[StockoutPeriod, ...]]:
    start, end = midnight(periods[0][0]), midnight(periods[-1][1] + timedelta(days=1))
    overlapping = [row for row in stockouts if utc(row.started_at) < end and
                   (row.ended_at is None or utc(row.ended_at) > start)]
    explicit = [row for row in overlapping if row.source in (StockoutSource.IMPORTED, StockoutSource.MANUAL)]
    selected = explicit or overlapping
    snapshots = sorted(snapshots, key=lambda row: (utc(row.snapshot_at), str(row.id)))
    unique = {}
    for row in snapshots:
        at = utc(row.snapshot_at)
        if at in unique and unique[at].quantity_available != row.quantity_available:
            raise AmbiguousSourceDataError("Conflicting inventory values at the same timestamp")
        unique.setdefault(at, row)
    snapshots = list(unique.values())
    if not selected and len(snapshots) >= config.stockout_min_snapshots:
        for first, last in zip(snapshots, snapshots[1:]):
            left, right = utc(first.snapshot_at), utc(last.snapshot_at)
            if (first.quantity_available <= 0 and last.quantity_available <= 0 and
                    ZERO < days(right - left) <= config.stockout_max_snapshot_gap_days and left < end and right > start):
                selected.append(StockoutPeriod(
                    id=uuid5(run_id, f"stockout:{first.id}:{last.id}"),
                    product_id=first.product_id, warehouse_id=first.warehouse_id,
                    started_at=left, ended_at=right, source=StockoutSource.INFERRED,
                ))
    selected = sorted(selected, key=lambda row: (utc(row.started_at), str(row.id)))
    missing_days, explanations = [], []
    for lower, upper in periods:
        left, right = midnight(lower), midnight(upper + timedelta(days=1))
        intervals, sources, evidence_ids = [], set(), []
        for row in selected:
            a, b = max(left, utc(row.started_at)), min(right, utc(row.ended_at) if row.ended_at else end)
            if b > a:
                intervals.append((a, b))
                sources.add(row.source.value)
                evidence_ids.append(str(row.id))
        merged: list[tuple[datetime, datetime]] = []
        for a, b in sorted(intervals):
            if merged and a <= merged[-1][1]:
                merged[-1] = merged[-1][0], max(merged[-1][1], b)
            else:
                merged.append((a, b))
        lost = sum((days(b - a) for a, b in merged), ZERO)
        missing_days.append(lost)
        explanations.append({
            "missing_days": str(lost), "sources": sorted(sources), "evidence_ids": evidence_ids,
            "confirmed": bool(sources) and StockoutSource.INFERRED.value not in sources,
            "reason": "no_stockout_evidence" if not sources else "insufficient_comparable_periods",
        })
    # Compare only the same SKU/warehouse, not recursively compensated periods.
    donors = []
    for index, (lower, upper) in enumerate(periods):
        positive_stock = any(lower <= utc(row.snapshot_at).date() <= upper and row.quantity_available > 0
                             for row in snapshots)
        if missing_days[index] == 0 and observed[index] and (cleaned[index] > 0 or positive_stock):
            donors.append(index)
    adjustments = [ZERO] * len(periods)
    for index, lost in enumerate(missing_days):
        if lost == 0:
            continue
        neighbors = sorted(donors, key=lambda candidate: (abs(candidate - index), candidate))[:config.stockout_baseline_neighbors]
        if len(neighbors) < config.stockout_min_baseline_periods:
            continue
        rates = [cleaned[candidate] / Decimal((periods[candidate][1] - periods[candidate][0]).days + 1)
                 for candidate in neighbors]
        rate = median(rates)
        adjustments[index] = rate * lost
        explanations[index].update({
            "reason": "median_comparable_daily_demand", "daily_rate": str(rate),
            "baseline_periods": [periods[candidate][0].isoformat() for candidate in neighbors],
        })
    return adjustments, explanations, tuple(selected)
