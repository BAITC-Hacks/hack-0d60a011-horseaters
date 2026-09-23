from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.domain.entities.order_export import OrderExport


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


@dataclass(frozen=True, slots=True)
class ExportedOrder:
    metadata: OrderExport
    content: bytes
    media_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
