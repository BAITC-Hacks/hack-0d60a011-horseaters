from __future__ import annotations

import re
from datetime import timedelta
from hashlib import sha256

from backend.application.dto.order import (
    ExportedOrderFile,
    OrderExportCommand,
    OrderExportRow,
)
from backend.application.ports.order_export import OrderWorkbookExporter
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus
from backend.domain.entities.order_export import OrderExport, utc_now


class OrderExportError(RuntimeError):
    pass


class OrderNotExportableError(OrderExportError):
    pass


class OrderExportReferenceError(OrderExportError):
    pass


class ExportOrder:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        workbook_exporter: OrderWorkbookExporter,
    ) -> None:
        self._uow_factory = uow_factory
        self._workbook_exporter = workbook_exporter

    def execute(self, command: OrderExportCommand) -> ExportedOrderFile:
        with self._uow_factory() as uow:
            order = uow.orders.get(command.order_id)
            if order is None:
                raise LookupError("purchase order not found")
            if order.status is not PurchaseOrderStatus.APPROVED:
                raise OrderNotExportableError("only an approved order can be exported")
            if order.approved_at is None:
                raise OrderNotExportableError("approved order has no approval timestamp")

            supplier = uow.suppliers.get_by_id(order.supplier_id)
            warehouse = uow.warehouses.get_by_id(order.warehouse_id)
            if supplier is None or warehouse is None:
                raise OrderExportReferenceError("order supplier or warehouse was not found")

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
                        f"product or supplier terms for order item {item.id} were not found"
                    )
                delivery_date = order.approved_at.date() + timedelta(
                    days=terms[0].lead_time_days
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
                        delivery_date=delivery_date,
                    )
                )

            content = self._workbook_exporter.render(rows)
            checksum = sha256(content).hexdigest()
            created_at = utc_now()
            safe_number = re.sub(
                r"[^A-Za-z0-9._-]+", "-", order.order_number
            ).strip("-.")
            file_name = f"order-{safe_number or order.id}.xlsx"
            metadata = OrderExport(
                purchase_order_id=order.id,
                format=ExportFormat.XLSX,
                file_name=file_name,
                file_checksum=checksum,
                created_by=command.user_id,
                created_at=created_at,
            )
            uow.orders.add_export(metadata)
            uow.commit()
            return ExportedOrderFile(
                content=content,
                file_name=file_name,
                checksum=checksum,
                created_at=created_at,
                metadata=metadata,
            )
