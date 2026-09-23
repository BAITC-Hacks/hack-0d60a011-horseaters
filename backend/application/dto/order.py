from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from backend.domain.entities.order_export import OrderExport


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderExportCommand:
    order_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderExportRow:
    order_number: str
    supplier_name: str
    warehouse_name: str
    sku: str
    product_name: str
    recommended_quantity: Decimal
    approved_quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None
    delivery_date: date


@dataclass(frozen=True, slots=True, kw_only=True)
class ExportedOrderFile:
    content: bytes
    file_name: str
    checksum: str
    created_at: datetime
    metadata: OrderExport
