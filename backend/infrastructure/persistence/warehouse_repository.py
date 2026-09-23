from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.entities.catalog import Warehouse
from backend.infrastructure.persistence.models.catalog import WarehouseModel
from ._read_repository import to_entity


class SqlAlchemyWarehouseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active_ids(self) -> list[UUID]:
        return list(self._session.scalars(
            select(WarehouseModel.id).where(WarehouseModel.is_active.is_(True)).order_by(WarehouseModel.id)
        ))

    def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        model = self._session.get(WarehouseModel, warehouse_id)
        return to_entity(model, Warehouse) if model is not None else None
