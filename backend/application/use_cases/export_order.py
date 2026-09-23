from __future__ import annotations

import re
from datetime import timedelta
from hashlib import sha256
from uuid import UUID

from backend.application.dto.order import ExportedOrder, OrderExportRow
from backend.application.ports.order_exporter import OrderExporter
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus
from backend.domain.entities.order_export import OrderExport
from backend.domain.repositories.order_repository import OrderNotFoundError


class OrderNotExportableError(ValueError):
    pass


class OrderExportReferenceError(ValueError):
    pass


class ExportOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory, exporter: OrderExporter) -> None:
        self._uow_factory = uow_factory
        self._exporter = exporter

    def execute(self, order_id: UUID, *, user_id: UUID) -> ExportedOrder:
        """Render XLSX and atomically record its checksum and export actor."""
        if not isinstance(user_id, UUID):
            raise ValueError("user_id must be a user UUID")
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(order_id)
            if order.status is not PurchaseOrderStatus.APPROVED:
                raise OrderNotExportableError("only an approved order can be exported")
            if order.approved_at is None:
                raise OrderNotExportableError(
                    "approved order has no approval timestamp"
                )

            supplier = uow.suppliers.get_by_id(order.supplier_id)
            warehouse = uow.warehouses.get_by_id(order.warehouse_id)
            if supplier is None or warehouse is None:
                raise OrderExportReferenceError(
                    "order supplier or warehouse is missing"
                )

            rows: list[OrderExportRow] = []
            for item in sorted(order.items, key=lambda value: str(value.product_id)):
                product = uow.products.get_by_id(item.product_id)
                terms = uow.suppliers.list_terms(
                    item.product_id,
                    supplier_id=order.supplier_id,
                    active_only=False,
                )
                if product is None or not terms:
                    raise OrderExportReferenceError(
                        f"product or supplier terms for order item {item.id} are missing"
                    )
                total_amount = item.total_amount
                if total_amount is None and item.unit_price is not None:
                    total_amount = item.approved_quantity * item.unit_price
                rows.append(
                    OrderExportRow(
                        order_number=order.order_number,
                        supplier_name=supplier.name,
                        warehouse_name=warehouse.name,
                        sku=product.sku,
                        product_name=product.name,
                        recommended_quantity=item.recommended_quantity,
                        approved_quantity=item.approved_quantity,
                        unit_price=item.unit_price,
                        total_amount=total_amount,
                        delivery_date=(
                            order.approved_at.date()
                            + timedelta(days=terms[0].lead_time_days)
                        ),
                    )
                )

            content = self._exporter.render(rows)
            if not isinstance(content, bytes) or not content:
                raise ValueError("exporter must return a nonempty XLSX byte sequence")
            safe_number = re.sub(
                r"[^A-Za-z0-9._-]+", "-", order.order_number
            ).strip("-.")
            metadata = OrderExport(
                purchase_order_id=order.id,
                format=ExportFormat.XLSX,
                file_name=f"order-{safe_number or order.id}.xlsx",
                file_checksum=sha256(content).hexdigest(),
                created_by=user_id,
            )
            saved = uow.orders.add_export(metadata)
            result = ExportedOrder(metadata=saved, content=content)
            uow.commit()
        return result
