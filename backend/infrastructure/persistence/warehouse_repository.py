from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.persistence.models.catalog import WarehouseModel


class SqlAlchemyWarehouseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active_ids(self) -> list[UUID]:
        return list(self._session.scalars(
            select(WarehouseModel.id).where(WarehouseModel.is_active.is_(True)).order_by(WarehouseModel.id)
        ))
