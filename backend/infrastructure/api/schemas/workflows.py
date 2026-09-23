from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.domain.entities.enums import CalculationRunStatus, PurchaseOrderStatus, RecommendationStatus, Urgency
from backend.domain.value_objects.demand import DemandSource


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunCalculationRequest(RequestModel):
    demand_source: DemandSource
    horizon_days: int = Field(gt=0, strict=True)
    warehouse_id: UUID | None = None
    category_id: UUID | None = None


class RunParameters(ReadModel):
    horizon_days: int | None = None
    demand_source: DemandSource | None = None
    warehouse_id: UUID | None = None
    category_id: UUID | None = None


class CalculationRunResponse(ReadModel):
    id: UUID
    status: CalculationRunStatus
    parameters: RunParameters
    started_at: datetime
    finished_at: datetime | None
    algorithm_version: str
    import_batch_ids: list[UUID]
    recommendation_count: int | None = None
    error_details: dict[str, str] | None = None

    @field_validator("error_details", mode="before")
    @classmethod
    def safe_error(cls, value):
        return {"code": "calculation_failed"} if value else None


class CalculationComponents(ReadModel):
    # Only documented calculation fields; arbitrary JSON can contain internal diagnostics.
    baseline: Decimal | None = None
    raw_demand: Decimal | None = None
    return_adjustment: Decimal | None = None
    anomaly_adjustment: Decimal | None = None
    stockout_compensation: Decimal | None = None
    growth_rate: Decimal | None = None
    growth_multiplier: Decimal | None = None
    seasonality_index: Decimal | None = None
    forecast: Decimal | None = None
    demand_during_horizon: Decimal | None = None
    coverage_days: int | None = None
    lead_time_days: int | None = None
    safety_stock: Decimal | None = None
    current_stock: Decimal | None = None
    in_transit: Decimal | None = None
    material_requirements: Decimal | None = None
    available_supply: Decimal | None = None
    shortage_quantity: Decimal | None = None
    quantity_before_rounding: Decimal | None = None
    moq: Decimal | None = None
    package_size: Decimal | None = None
    quantity_after_rounding: Decimal | None = None
    risk_score: Decimal | None = None
    urgency: Urgency | None = None
    shortage_ratio: Decimal | None = None
    lead_time_gap_ratio: Decimal | None = None
    expected_stockout_at: datetime | None = None


class RecommendationResponse(ReadModel):
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
    calculation_details: CalculationComponents
    created_at: datetime
    updated_at: datetime


class RecommendationFilters(RequestModel):
    supplier_id: UUID | None = None
    warehouse_id: UUID | None = None
    category_id: UUID | None = None
    urgency: Urgency | None = None
    status: RecommendationStatus | None = None
    sort_by: Literal["risk_score", "recommended_quantity", "created_at", "urgency", "product_id"] = "risk_score"
    descending: bool = True
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class RecommendationPageResponse(ReadModel):
    items: list[RecommendationResponse]
    total: int
    limit: int
    offset: int


class AdjustRecommendationRequest(RequestModel):
    new_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    version: int = Field(gt=0, strict=True)


class AnomalyResponse(ReadModel):
    id: UUID
    sales_transaction_id: UUID
    method: str
    original_quantity: Decimal
    replacement_quantity: Decimal
    threshold: Decimal | None
    reason: str


class ForecastResponse(ReadModel):
    id: UUID
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


class ExplanationResponse(ReadModel):
    recommendation_id: UUID
    formula: str
    components: CalculationComponents
    anomalies: list[AnomalyResponse]
    forecast: ForecastResponse
    text: str


class CreateOrdersRequest(RequestModel):
    calculation_run_id: UUID


class OrderItemResponse(ReadModel):
    id: UUID
    recommendation_id: UUID
    product_id: UUID
    recommended_quantity: Decimal
    approved_quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None


class OrderResponse(ReadModel):
    id: UUID
    order_number: str
    supplier_id: UUID
    warehouse_id: UUID
    created_from_run_id: UUID
    status: PurchaseOrderStatus
    created_by: UUID
    created_at: datetime
    approved_by: UUID | None
    approved_at: datetime | None
    exported_at: datetime | None
    items: list[OrderItemResponse]


class ExportResponse(ReadModel):
    id: UUID
    purchase_order_id: UUID
    format: Literal["xlsx"]
    file_name: str
    file_checksum: str
    created_by: UUID
    created_at: datetime
