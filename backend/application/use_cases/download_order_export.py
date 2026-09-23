from hashlib import sha256
from uuid import UUID

from backend.application.dto.order import ExportedOrder
from backend.application.ports.export_artifacts import ExportArtifactStore, ExportArtifactUnavailableError
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.enums import ExportFormat, PurchaseOrderStatus
from backend.domain.repositories.order_repository import OrderNotFoundError


class DownloadOrderExport:
    def __init__(self, uow_factory: UnitOfWorkFactory, artifact_store: ExportArtifactStore) -> None:
        self._uow_factory = uow_factory
        self._artifact_store = artifact_store

    def execute(self, order_id: UUID) -> ExportedOrder:
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(order_id)
            exports = uow.orders.list_exports(order_id)
            rows = [row for row in exports if row.format is ExportFormat.XLSX]
            if order.status is not PurchaseOrderStatus.EXPORTED or not rows:
                raise LookupError("No completed XLSX export")
            metadata = max(rows, key=lambda row: (row.created_at, row.id))
        content = self._artifact_store.read(metadata.id)
        if sha256(content).hexdigest() != metadata.file_checksum:
            raise ExportArtifactUnavailableError("Export checksum mismatch")
        return ExportedOrder(metadata=metadata, content=content)
