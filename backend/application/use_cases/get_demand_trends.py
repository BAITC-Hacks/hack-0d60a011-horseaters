"""Read saved historical components for category charts; never recalculate."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class DemandTrendPoint:
    category_id: UUID | None
    period_start: date
    period_end: date
    raw_demand: Decimal
    cleaned_demand: Decimal
    stockout_adjustment: Decimal


class GetDemandTrends:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, run_id: UUID, *, category_id: UUID | None = None,
                warehouse_id: UUID | None = None) -> list[DemandTrendPoint] | None:
        with self._uow_factory() as uow:
            if uow.calculation_runs.get(run_id) is None:
                return None
            totals: dict[tuple[UUID | None, date, date], list[Decimal]] = {}
            for forecast in uow.calculation_runs.list_forecasts(run_id):
                if warehouse_id is not None and forecast.warehouse_id != warehouse_id:
                    continue
                # A category change after the run must not regroup saved history.
                stored_category = forecast.details.get("category_id")
                forecast_category = UUID(stored_category) if stored_category else None
                if category_id is not None and forecast_category != category_id:
                    continue
                for period in forecast.details.get("monthly_history", []):
                    start = date.fromisoformat(period["period_start"])
                    end = date.fromisoformat(period["period_end"])
                    values = totals.setdefault((forecast_category, start, end),
                                               [Decimal("0"), Decimal("0"), Decimal("0")])
                    values[0] += Decimal(str(period["raw_demand"]))
                    values[1] += Decimal(str(period["cleaned_demand"]))
                    values[2] += Decimal(str(period["stockout_adjustment"]))
        return [DemandTrendPoint(key[0], key[1], key[2], *values)
                for key, values in sorted(totals.items(), key=lambda item: (
                    item[0][1], str(item[0][0]), item[0][2]))]
