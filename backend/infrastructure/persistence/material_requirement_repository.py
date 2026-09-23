from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.imports import MaterialRequirement
from backend.domain.enums import MaterialRequirementStatus
from backend.domain.repositories.material_requirement_repository import MaterialRequirementRepository
from ._read_repository import SqlAlchemyReadRepository, time_range, visible_import
from .models.imports import MaterialRequirementModel


class SqlAlchemyMaterialRequirementRepository(SqlAlchemyReadRepository, MaterialRequirementRepository):
    def list_requirements(
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        status: MaterialRequirementStatus | None = MaterialRequirementStatus.PLANNED,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[MaterialRequirement]:
        start, end = time_range(start, end)
        model = MaterialRequirementModel
        query = select(model).where(
            model.required_at >= start, model.required_at < end,
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if product_id is not None:
            query = query.where(model.product_id == product_id)
        if warehouse_id is not None:
            query = query.where(model.warehouse_id == warehouse_id)
        if status is not None:
            query = query.where(model.status == status)
        return self._read(query.order_by(model.required_at, model.id), MaterialRequirement)
