"""Read sources through existing ports and return domain preparation results."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, timedelta
from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.calculation_run import CalculationRun
from backend.domain.enums import ImportStatus, TransactionType
from backend.domain.services._demand_math import calendar, midnight, utc
from backend.domain.services.demand_preparation import prepare_demand
from backend.domain.value_objects.demand import DemandConfig, DemandGroup, DemandPreparationResult, DemandSource


class PrepareDemand:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(
        self, run: CalculationRun, *, start: date, end: date,
        groups: Sequence[tuple[UUID, UUID | None]], config: DemandConfig = DemandConfig(),
        growth_assumption_ids: Mapping[tuple[UUID, UUID | None], UUID] | None = None,
    ) -> DemandPreparationResult:
        """run.parameters['demand_source'] is mandatory; no auto source/override choice.

        Uses the run's fixed import whitelist. Local manual/inferred stockouts and
        explicitly chosen growth assumptions can have NULL import_batch_id.
        Does not start/complete the run or persist/commit anything.
        """
        source = DemandSource(run.parameters.get("demand_source"))
        calendar(start, end)
        lower, upper, cutoff = midnight(start), midnight(end + timedelta(days=1)), utc(run.source_cutoff_at)
        if upper > cutoff:
            raise ValueError("History must consist of complete months at the source cutoff")
        if not run.import_batch_ids:
            raise ValueError("Select the run's import batches explicitly before preparing demand")
        if len(set(groups)) != len(groups):
            raise ValueError("Duplicate SKU/warehouse groups")
        if set(growth_assumption_ids or {}) - set(groups):
            raise ValueError("Growth selections must reference requested groups")
        batches = tuple(sorted(run.import_batch_ids, key=str))
        demand_groups, transactions, monthly, snapshots, stockouts, overrides = [], {}, [], [], [], {}
        with self._uow_factory() as uow:
            for batch_id in batches:
                batch = uow.imports.get(batch_id)
                if batch is None or batch.status is not ImportStatus.COMPLETED or utc(batch.imported_at) > cutoff:
                    raise ValueError("Run imports must be completed and imported no later than source_cutoff_at")
            growth_rows = uow.seasonality.list_growth_assumptions(cutoff.date()) if growth_assumption_ids else []
            growth_by_id = {row.id: row for row in growth_rows if row.import_batch_id is None or row.import_batch_id in batches}
            for product_id, warehouse_id in groups:
                product = uow.products.get_by_id(product_id)
                if product is None:
                    raise ValueError(f"Unknown product {product_id}")
                if run.warehouse_id is not None and warehouse_id != run.warehouse_id:
                    raise ValueError("Group warehouse differs from the run filter")
                if run.category_id is not None and product.category_id != run.category_id:
                    raise ValueError("Group category differs from the run filter")
                if source is DemandSource.TRANSACTIONS and warehouse_id is None:
                    raise ValueError("Transaction groups must specify a warehouse")
                demand_groups.append(DemandGroup(product=product, warehouse_id=warehouse_id))
                if source is DemandSource.TRANSACTIONS:
                    rows = uow.sales.list_transactions(lower, upper, product_id=product_id,
                                                       warehouse_id=warehouse_id, import_batch_ids=batches)
                    sale_ids = [row.id for row in rows if row.transaction_type is TransactionType.SALE]
                    rows += uow.sales.list_returns_for_sales(sale_ids, as_of=cutoff, import_batch_ids=batches)
                    for row in rows:
                        transactions[row.id] = row
                    references = {row.original_transaction_id for row in rows if row.original_transaction_id is not None}
                    for row in uow.sales.get_transactions_by_ids(references - transactions.keys(), as_of=cutoff,
                                                                 import_batch_ids=batches):
                        transactions[row.id] = row
                else:
                    monthly.extend(uow.sales.list_monthly_sales(start, end, product_id=product_id,
                                                               warehouse_id=warehouse_id, import_batch_ids=batches))
                if warehouse_id is not None:
                    snapshots.extend(uow.inventory.list_snapshots(
                        product_id, warehouse_id, started_at=lower - timedelta(days=config.stockout_max_snapshot_gap_days),
                        ended_at=upper, import_batch_ids=batches,
                    ))
                    stockouts.extend(row for row in uow.inventory.list_stockout_periods(
                        lower, upper, product_id=product_id, warehouse_id=warehouse_id,
                    ) if row.import_batch_id is None or row.import_batch_id in batches)
                assumption_id = (growth_assumption_ids or {}).get((product_id, warehouse_id))
                if assumption_id is not None:
                    if assumption_id not in growth_by_id:
                        raise ValueError("Selected growth assumption is missing, expired or outside the run imports")
                    overrides[(product_id, warehouse_id)] = growth_by_id[assumption_id]
        result = prepare_demand(
            calculation_run_id=run.id, source=source, start=start, end=end, source_cutoff_at=cutoff,
            groups=demand_groups, transactions=tuple(transactions.values()), monthly_sales=monthly,
            stockouts=stockouts, snapshots=snapshots, growth_overrides=overrides, config=config,
        )
        return replace(result, parameters={**result.parameters, "algorithm_version": run.algorithm_version,
                                           "import_batch_ids": [str(batch) for batch in batches]})
