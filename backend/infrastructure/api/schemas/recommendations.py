from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.entities.enums import RecommendationStatus, Urgency


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    calculation_run_id: UUID
    product_id: UUID
    warehouse_id: UUID
    supplier_id: UUID
    forecast_quantity: Decimal
    current_stock: Decimal
    in_transit_quantity: Decimal
    material_requirement_quantity: Decimal
    safety_stock: Decimal
    shortage_quantity: Decimal
    quantity_before_rounding: Decimal
    moq: Decimal
    package_size: Decimal
    recommended_quantity: Decimal
    effective_quantity: Decimal
    risk_score: Decimal
    urgency: Urgency
    status: RecommendationStatus
    version: int
    explanation: str
    calculation_details: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RecommendationPageResponse(BaseModel):
    items: list[RecommendationResponse]
    total: int = Field(ge=0)
    limit: int = Field(gt=0)
    offset: int = Field(ge=0)


class AdjustRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    version: int = Field(gt=0)
    new_quantity: Decimal = Field(ge=0)
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


class RecommendationAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_id: UUID
    previous_quantity: Decimal
    new_quantity: Decimal
    reason: str
    changed_by: UUID
    changed_at: datetime


class DemandForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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
    details: dict[str, Any]


class DetectedAnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    calculation_run_id: UUID
    sales_transaction_id: UUID
    method: str
    original_quantity: Decimal
    replacement_quantity: Decimal
    reason: str
    threshold: Decimal | None
    details: dict[str, Any]


class RecommendationExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: UUID
    formula: str
    components: dict[str, Any]
    anomalies: list[DetectedAnomalyResponse]
    forecast: DemandForecastResponse
    text: str
