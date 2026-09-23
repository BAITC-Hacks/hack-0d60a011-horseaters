from dataclasses import dataclass

from backend.domain.entities.order_export import OrderExport


@dataclass(frozen=True, slots=True)
class ExportedOrder:
    metadata: OrderExport
    content: bytes
    media_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
