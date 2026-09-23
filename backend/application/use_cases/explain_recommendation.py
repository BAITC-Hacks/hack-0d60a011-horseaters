from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.entities.detected_anomaly import DetectedAnomaly


@dataclass(frozen=True, slots=True)
class RecommendationExplanation:
    recommendation_id: UUID
    formula: str
    components: Mapping[str, Any]
    anomalies: list[DetectedAnomaly]
    forecast: DemandForecast
    text: str


class ExplainRecommendation:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, recommendation_id: UUID) -> RecommendationExplanation | None:
        with self._uow_factory() as uow:
            recommendation = uow.recommendations.get(recommendation_id)
            if recommendation is None:
                return None
            forecast = uow.calculation_runs.get_forecast(
                recommendation.calculation_run_id,
                recommendation.product_id,
                recommendation.warehouse_id,
            )
            if forecast is None:
                raise LookupError("forecast for recommendation not found")
            anomalies = uow.calculation_runs.list_anomalies(
                recommendation.calculation_run_id,
                recommendation.product_id,
                recommendation.warehouse_id,
            )
            details = dict(recommendation.calculation_details)
            return RecommendationExplanation(
                recommendation_id=recommendation.id,
                formula=("max(0, forecast / forecast_days * (horizon_days + lead_time_days) "
                         "+ safety_stock + material_requirements - current_stock - in_transit), "
                         "rounded to MOQ/package_size"),
                components=details, anomalies=anomalies, forecast=forecast,
                text=recommendation.explanation,
            )
