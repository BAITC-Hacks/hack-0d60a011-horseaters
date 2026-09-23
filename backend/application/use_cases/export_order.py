from hashlib import sha256
from uuid import UUID

from backend.application.dto.order import ExportedOrder
from backend.application.ports.order_exporter import OrderExporter
from backend.application.ports.export_artifacts import ExportArtifactStore
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus
from backend.domain.entities.order_export import OrderExport
from backend.domain.repositories.order_repository import OrderNotFoundError
from backend.domain.errors import InvalidEntityStateError


class ExportOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory, exporter: OrderExporter,
                 artifact_store: ExportArtifactStore | None = None) -> None:
        self._uow_factory = uow_factory
        self._exporter = exporter
        self._artifact_store = artifact_store

    def execute(self, order_id: UUID, *, user_id: UUID) -> ExportedOrder:
        """Return bytes after committing export audit; file_name is a download name, not a path."""
        if not isinstance(user_id, UUID):
            raise ValueError("user_id must be a user UUID")
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(order_id)
            if order.status is not PurchaseOrderStatus.APPROVED:
                raise InvalidEntityStateError("only an approved order can be exported")
            supplier = uow.suppliers.get_by_id(order.supplier_id)
            warehouse = uow.warehouses.get_by_id(order.warehouse_id)
            if supplier is None or warehouse is None:
                raise ValueError("Order supplier or warehouse is missing")
            products = {}
            for item in order.items:
                product = uow.products.get_by_id(item.product_id)
                if product is None:
                    raise ValueError(f"Order product {item.product_id} is missing")
                products[product.id] = product
            content = self._exporter.render(order, supplier=supplier, warehouse=warehouse, products=products)
            if not isinstance(content, bytes) or not content:
                raise ValueError("Exporter must return a nonempty XLSX byte sequence")
            metadata = OrderExport(purchase_order_id=order.id, format=ExportFormat.XLSX,
                                   file_name=f"order-{order.id}.xlsx", file_checksum=sha256(content).hexdigest(),
                                   created_by=user_id)
            if self._artifact_store is not None:
                # File first, then metadata/status in one DB commit. A failed DB commit
                # may leave an unreferenced artifact; GET never discovers files by scanning.
                self._artifact_store.put(metadata.id, content)
            saved = uow.orders.add_export(metadata)
            result = ExportedOrder(metadata=saved, content=content)
            uow.commit()
        return result
