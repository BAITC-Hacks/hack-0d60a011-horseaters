from typing import Protocol
from uuid import UUID

from backend.domain.entities.calculation_run import CalculationRun
from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.entities.detected_anomaly import DetectedAnomaly


class CalculationRunRepository(Protocol):
    def get(self, run_id: UUID) -> CalculationRun | None: ...

    def add(self, run: CalculationRun) -> None: ...

    def save(self, run: CalculationRun) -> None: ...

    def add_results(
        self,
        forecasts: list[DemandForecast],
        anomalies: list[DetectedAnomaly],
    ) -> None: ...

    def get_forecast(
        self, run_id: UUID, product_id: UUID, warehouse_id: UUID
    ) -> DemandForecast | None: ...

    def list_anomalies(
        self, run_id: UUID, product_id: UUID, warehouse_id: UUID
    ) -> list[DetectedAnomaly]: ...
