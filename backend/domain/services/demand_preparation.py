"""ALG-01 through ALG-05 on domain objects, with no I/O or persistence."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from uuid import UUID

from backend.domain.entities.imports import (
    GrowthAssumption, InventorySnapshot, MonthlySales, SalesTransaction, StockoutPeriod,
)
from backend.domain.enums import TransactionType
from backend.domain.repositories.filters import AmbiguousSourceDataError
from backend.domain.value_objects.demand import (
    DemandConfig, DemandGroup, DemandPreparationResult, DemandSource, PeriodAnomaly,
    PreparedDemandPeriod, PreparedDemandSeries,
)
from ._demand_math import ZERO, calendar, midnight, utc
from .anomaly import clean_transactions, iqr_rule
from .growth import estimate_growth
from .stockout import compensate_stockout


def _unique(rows: Sequence) -> None:
    if len({row.id for row in rows}) != len(rows):
        raise ValueError("Duplicate source row IDs; provide each fact exactly once")


def prepare_demand(
    *, calculation_run_id: UUID, source: DemandSource, start: date, end: date,
    source_cutoff_at: datetime, groups: Sequence[DemandGroup],
    transactions: Sequence[SalesTransaction] = (), monthly_sales: Sequence[MonthlySales] = (),
    stockouts: Sequence[StockoutPeriod] = (), snapshots: Sequence[InventorySnapshot] = (),
    growth_overrides: Mapping[tuple[UUID, UUID | None], GrowthAssumption] | None = None,
    config: DemandConfig = DemandConfig(),
    allow_partial_final_month: bool = False,
) -> DemandPreparationResult:
    """Prepare complete UTC months; linked returns are known up to the inclusive cutoff.

    The caller supplies explicit groups, including groups with no source facts.
    Only the selected demand source is examined. Missing linked sales are errors,
    not reclassified as unlinked returns. No implicit growth-assumption priority.
    """
    if not isinstance(source, DemandSource):
        raise TypeError("source must be DemandSource")
    if allow_partial_final_month and source is DemandSource.MONTHLY_SALES:
        raise ValueError("Monthly aggregates require complete calendar months")
    periods = calendar(start, end, allow_partial_final_month=allow_partial_final_month)
    cutoff = utc(source_cutoff_at)
    if (midnight(end) if allow_partial_final_month else midnight(end + timedelta(days=1))) > cutoff:
        raise ValueError("The historical calendar must be complete at source_cutoff_at")
    keys = [group.key for group in groups]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate SKU/warehouse groups")
    if source is DemandSource.TRANSACTIONS and any(group.warehouse_id is None for group in groups):
        raise ValueError("Transaction groups must specify a warehouse")
    if set(growth_overrides or {}) - set(keys):
        raise ValueError("Growth overrides must reference requested groups")
    selected = transactions if source is DemandSource.TRANSACTIONS else monthly_sales
    _unique(selected)
    if source is DemandSource.TRANSACTIONS:
        known = {row.id: row for row in transactions if utc(row.sold_at) <= cutoff}
        for row in known.values():
            original = known.get(row.original_transaction_id)
            if original is not None and (original.product_id, original.warehouse_id) in keys:
                if (original.transaction_type is not TransactionType.SALE or
                        (row.product_id, row.warehouse_id) != (original.product_id, original.warehouse_id) or
                        utc(original.sold_at) > utc(row.sold_at)):
                    raise ValueError("Linked return must reference an earlier sale of the same SKU and warehouse")
    _unique(stockouts)
    _unique(snapshots)
    series = []
    # Results must not depend on the caller's Decimal precision or input ordering.
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        for group in sorted(groups, key=lambda item: (str(item.product.id), str(item.warehouse_id))):
            series.append(_prepare_group(group, periods, source, cutoff, selected, stockouts, snapshots,
                                         (growth_overrides or {}).get(group.key), calculation_run_id, config,
                                         allow_partial_final_month))
    parameters = {name: str(value) if isinstance(value, Decimal) else value for name, value in asdict(config).items()}
    parameters.update({"demand_source": source.value, "period_granularity": "calendar_month_utc",
                       "partial_final_month": allow_partial_final_month,
                       "return_handling": ("linked_to_original_sale_unlinked_to_return_month"
                                           if source is DemandSource.TRANSACTIONS else "unavailable_monthly_aggregate"),
                       "pipeline_version": "ALG-01-05/v1", "decimal_precision": 28})
    return DemandPreparationResult(
        calculation_run_id=calculation_run_id, source=source, period_start=start, period_end=end,
        source_cutoff_at=cutoff, series=tuple(series), parameters=parameters,
    )


def _prepare_group(group, periods, source, cutoff, selected, stockouts, snapshots, override, run_id,
                   config, partial_last):
    months = {lower: index for index, (lower, _) in enumerate(periods)}
    start, end = periods[0][0], periods[-1][1]
    raw, returns, anomaly_delta = ([ZERO] * len(periods) for _ in range(3))
    observed = [False] * len(periods)
    source_ids = [[] for _ in periods]
    limitations, anomalies, period_anomalies = [], (), []
    customer_check = "not_applicable_monthly_source"

    def period_index(at):
        return months.get(utc(at).date().replace(day=1))

    if source is DemandSource.TRANSACTIONS:
        all_rows = {row.id: row for row in selected if utc(row.sold_at) <= cutoff}
        rows = sorted((row for row in all_rows.values() if (row.product_id, row.warehouse_id) == group.key),
                      key=lambda row: (utc(row.sold_at), str(row.id)))
        sales = [row for row in rows if row.transaction_type is TransactionType.SALE and period_index(row.sold_at) is not None]
        net = {row.id: row.quantity for row in sales}
        for sale in sales:
            index = period_index(sale.sold_at)
            raw[index] += sale.quantity
            observed[index] = True
            source_ids[index].append(str(sale.id))
        for row in rows:
            if row.transaction_type is not TransactionType.RETURN:
                continue
            index = period_index(row.sold_at)
            if row.original_transaction_id is not None:
                original = all_rows.get(row.original_transaction_id)
                if original is None:
                    raise ValueError(f"Original sale {row.original_transaction_id} is missing for linked return {row.id}")
                if (original.transaction_type is not TransactionType.SALE or
                        (original.product_id, original.warehouse_id) != group.key or utc(original.sold_at) > utc(row.sold_at)):
                    raise ValueError("Linked return must reference an earlier sale of the same SKU and warehouse")
                index = period_index(original.sold_at)
                if index is None:
                    limitations.append("linked_return_targets_sale_outside_calendar")
                    continue
                net[original.id] += row.quantity
            if index is not None:
                returns[index] += row.quantity
                observed[index] = True
                source_ids[index].append(str(row.id))
        if any(value < 0 for value in net.values()):
            limitations.append("linked_returns_exceed_original_quantity")
        net = {key: max(ZERO, value) for key, value in net.items()}
        cleaned, anomalies, customer_check = clean_transactions(sales, net, run_id, config)
        for sale in sales:
            anomaly_delta[period_index(sale.sold_at)] += cleaned[sale.id] - net[sale.id]
        if customer_check != "checked":
            limitations.append(customer_check)
    else:
        limitations.append("monthly_sales_has_no_transaction_return_or_customer_details")
        for row in sorted(selected, key=lambda item: str(item.id)):
            if (row.product_id, row.warehouse_id) != group.key or row.period_end < start or row.period_start > end:
                continue
            index = months.get(row.period_start)
            if index is None or periods[index] != (row.period_start, row.period_end):
                raise ValueError("Monthly source rows must cover exactly one full requested month; no implicit prorating")
            if observed[index]:
                raise AmbiguousSourceDataError("Multiple monthly aggregates for the same SKU/warehouse/month; select imports explicitly")
            raw[index] = row.quantity
            observed[index] = True
            source_ids[index].append(str(row.id))
        rule = iqr_rule(raw, config)
        if rule:
            threshold, replacement = rule
            for index, quantity in enumerate(raw):
                if quantity > threshold:
                    anomaly_delta[index] = replacement - quantity
                    period_anomalies.append(PeriodAnomaly(
                        period_start=periods[index][0], period_end=periods[index][1],
                        source_row_ids=tuple(UUID(value) for value in source_ids[index]),
                        original_quantity=quantity, replacement_quantity=replacement, threshold=threshold,
                    ))
        if any(value < 0 for value in raw):
            limitations.append("negative_monthly_net_demand_clipped_without_inventing_returns")
        if period_anomalies:
            limitations.append("monthly_anomalies_cannot_use_transaction_foreign_key")

    after_anomalies = [max(ZERO, a + b + c) for a, b, c in zip(raw, returns, anomaly_delta)]
    group_stockouts = [row for row in stockouts if (row.product_id, row.warehouse_id) == group.key and utc(row.started_at) <= cutoff]
    group_snapshots = [row for row in snapshots if (row.product_id, row.warehouse_id) == group.key and utc(row.snapshot_at) <= cutoff]
    compensation, stockout_details, evidence = compensate_stockout(
        periods, after_anomalies, observed, group_stockouts, group_snapshots, run_id, config,
    )
    if group.warehouse_id is None:
        limitations.append("warehouse_unknown_stockout_not_inferred")
    cleaned = [value + adjustment for value, adjustment in zip(after_anomalies, compensation)]
    if override is not None:
        on_date = cutoff.date()
        if (override.product_id is not None and override.product_id != group.product.id or
                override.category_id is not None and override.category_id != group.product.category_id or
                override.warehouse_id is not None and override.warehouse_id != group.warehouse_id or
                override.valid_from > on_date or override.valid_to is not None and override.valid_to < on_date):
            raise ValueError("Growth assumption does not apply to the group at source_cutoff_at")
    daily_rates = [value / Decimal((upper - lower).days + 1)
                   for value, (lower, upper) in zip(cleaned, periods)]
    # Today's incomplete month can drive the current forecast, but must not
    # masquerade as a complete month in the sustained-growth comparison.
    if partial_last:
        daily_rates = daily_rates[:-1]
    growth = estimate_growth(daily_rates, config, override)
    result_periods = []
    for index, (lower, upper) in enumerate(periods):
        calculated = cleaned[index] * growth.factor
        floor = max(ZERO, -(raw[index] + returns[index] + anomaly_delta[index]))
        result_periods.append(PreparedDemandPeriod(
            period_start=lower, period_end=upper, raw_demand=raw[index], return_adjustment=returns[index],
            demand_after_returns=max(ZERO, raw[index] + returns[index]), anomaly_adjustment=anomaly_delta[index],
            nonnegative_adjustment=floor, stockout_adjustment=compensation[index], cleaned_demand=cleaned[index],
            growth_adjustment=calculated - cleaned[index], calculated_demand=calculated, observed=observed[index],
            details={"source_row_ids": sorted(source_ids[index]), "stockout": stockout_details[index]},
        ))
    return PreparedDemandSeries(
        product_id=group.product.id, sku=group.product.sku, warehouse_id=group.warehouse_id, unit=group.product.unit,
        source=source, periods=tuple(result_periods), growth=growth, anomalies=anomalies,
        period_anomalies=tuple(period_anomalies), stockout_periods=evidence,
        customer_check=customer_check, limitations=tuple(sorted(set(limitations))),
    )
