from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.purchase_order import PurchaseOrder
from backend.domain.repositories.order_repository import OrderNotFoundError


class GetOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, order_id: UUID) -> PurchaseOrder:
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(order_id)
            return order
