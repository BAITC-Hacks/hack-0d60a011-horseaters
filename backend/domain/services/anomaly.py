"""IQR filtering of calculation copies, including customer/month concentration."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid5

from backend.domain.entities.detected_anomaly import DetectedAnomaly
from backend.domain.entities.imports import SalesTransaction
from backend.domain.value_objects.demand import DemandConfig
from ._demand_math import ZERO, median, quantile, utc


def iqr_rule(values: list[Decimal], config: DemandConfig) -> tuple[Decimal, Decimal] | None:
    # Empty calendar periods are not evidence of regular positive transaction size.
    positive = [value for value in values if value > 0]
    if len(positive) < config.anomaly_min_samples:
        return None
    q1, q3 = quantile(positive, Decimal("0.25")), quantile(positive, Decimal("0.75"))
    replacement = median(positive)
    spread = q3 - q1
    threshold = q3 + config.iqr_multiplier * spread
    if spread == 0:
        threshold = max(threshold, replacement * config.zero_iqr_multiplier)
    return threshold, replacement


def clean_transactions(
    sales: list[SalesTransaction], net: dict[UUID, Decimal], run_id: UUID, config: DemandConfig,
) -> tuple[dict[UUID, Decimal], tuple[DetectedAnomaly, ...], str]:
    cleaned = dict(net)
    anomalies = []

    def record(sale, before, after, threshold, method, details):
        anomalies.append(DetectedAnomaly(
            id=uuid5(run_id, f"{method}:{sale.id}"), calculation_run_id=run_id,
            sales_transaction_id=sale.id, method=method,
            original_quantity=sale.quantity, replacement_quantity=after, threshold=threshold,
            reason="Quantity exceeds the positive-sample IQR threshold; replaced only in the calculation",
            details={"demand_before": str(before), "demand_after": str(after), **details},
        ))

    rule = iqr_rule(list(net.values()), config)
    if rule:
        threshold, replacement = rule
        for sale in sales:
            if net[sale.id] > threshold:
                cleaned[sale.id] = replacement
                record(sale, net[sale.id], replacement, threshold, "transaction_iqr", {})

    customers: dict[str, dict[date, list[SalesTransaction]]] = defaultdict(lambda: defaultdict(list))
    for sale in sales:
        if sale.anonymous_customer_id and sale.anonymous_customer_id.strip():
            month = utc(sale.sold_at).date().replace(day=1)
            customers[sale.anonymous_customer_id][month].append(sale)
    checked = False
    for customer, months in sorted(customers.items()):
        totals = {month: sum((cleaned[sale.id] for sale in rows), ZERO) for month, rows in months.items()}
        rule = iqr_rule(list(totals.values()), config)
        if not rule:
            continue
        checked = True
        threshold, replacement = rule
        for month, rows in sorted(months.items()):
            total = totals[month]
            if total <= threshold:
                continue
            remaining = replacement
            positive = sorted((row for row in rows if cleaned[row.id] > 0), key=lambda row: str(row.id))
            for index, sale in enumerate(positive):
                before = cleaned[sale.id]
                after = remaining if index == len(positive) - 1 else replacement * before / total
                remaining -= after
                cleaned[sale.id] = after
                record(sale, before, after, threshold, "customer_period_iqr", {
                    "anonymous_customer_id": customer, "period_start": month.isoformat(),
                    "customer_period_before": str(total), "customer_period_after": str(replacement),
                })
    status = "checked" if checked else "insufficient_customer_history" if customers else "unavailable_no_customer_ids"
    if checked and any(not (sale.anonymous_customer_id or "").strip() for sale in sales):
        status = "checked_partial_customer_coverage"
    return cleaned, tuple(sorted(anomalies, key=lambda row: (str(row.sales_transaction_id), row.method))), status
