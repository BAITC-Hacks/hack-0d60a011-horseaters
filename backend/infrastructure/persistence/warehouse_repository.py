from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.entities.catalog import Warehouse
from backend.infrastructure.persistence._read_repository import SqlAlchemyReadRepository
from backend.infrastructure.persistence.models.catalog import WarehouseModel


class SqlAlchemyWarehouseRepository(SqlAlchemyReadRepository):
    def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        rows = self._read(
            select(WarehouseModel).where(WarehouseModel.id == warehouse_id),
            Warehouse,
        )
        return rows[0] if rows else None

    def list_active_ids(self) -> list[UUID]:
        return list(self._session.scalars(
            select(WarehouseModel.id).where(WarehouseModel.is_active.is_(True)).order_by(WarehouseModel.id)
        ))
