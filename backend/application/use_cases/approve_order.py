from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.purchase_order import PurchaseOrder
from backend.domain.entities.enums import PurchaseOrderStatus
from backend.domain.repositories.order_repository import OrderNotFoundError


class ApproveOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, order_id: UUID, *, user_id: UUID) -> PurchaseOrder:
        """Caller supplies an authenticated/authorized actor; no auth service exists yet."""
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(order_id)
            order.approve(approved_by=user_id)
            approved = uow.orders.save(order, expected_status=PurchaseOrderStatus.DRAFT)
            uow.commit()
        return approved
