from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.imports import ImportBatch


class GetImportStatus:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, batch_id: UUID) -> ImportBatch:
        with self._uow_factory() as uow:
            batch = uow.imports.get(batch_id)
            if batch is None:
                raise LookupError("Import batch not found")
            return batch
