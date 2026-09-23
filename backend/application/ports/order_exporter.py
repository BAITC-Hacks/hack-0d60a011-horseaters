from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from backend.domain.entities.catalog import Supplier, Warehouse
from backend.domain.entities.product import Product
from backend.domain.entities.purchase_order import PurchaseOrder


class OrderExporter(Protocol):
    def render(self, order: PurchaseOrder, *, supplier: Supplier, warehouse: Warehouse,
               products: Mapping[UUID, Product]) -> bytes:
        """Return the complete XLSX file, or raise without recording an export."""
        ...
