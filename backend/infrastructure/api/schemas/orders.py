from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus


class CreateOrdersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    calculation_run_id: UUID
    recommendation_ids: list[UUID] | None = None


class ApproveOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_id: UUID
    product_id: UUID
    recommended_quantity: Decimal
    approved_quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    supplier_id: UUID
    warehouse_id: UUID
    created_from_run_id: UUID
    created_by: UUID
    status: PurchaseOrderStatus
    created_at: datetime
    approved_by: UUID | None
    approved_at: datetime | None
    exported_at: datetime | None
    items: list[OrderItemResponse]


class CreateOrdersResponse(BaseModel):
    orders: list[OrderResponse] = Field(default_factory=list)


class OrderExportMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_order_id: UUID
    format: ExportFormat
    file_name: str
    file_checksum: str
    created_by: UUID
    created_at: datetime
