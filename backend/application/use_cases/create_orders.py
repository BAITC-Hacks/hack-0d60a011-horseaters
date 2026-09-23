from collections import defaultdict
from uuid import UUID, uuid4

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.entities.recommendation import Recommendation, utc_now


class CreateOrders:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, calculation_run_id: UUID, *, user_id: UUID) -> tuple[PurchaseOrder, ...]:
        """Create only new drafts for one run; an already consumed selection returns ()."""
        if not isinstance(user_id, UUID):
            raise ValueError("user_id must be a user UUID")
        orders = []
        with self._uow_factory() as uow:
            groups: dict[tuple[UUID, UUID], list[Recommendation]] = defaultdict(list)
            now = utc_now()
            # Claim in stable global ID order to avoid deadlocks between batch creators.
            for recommendation in sorted(uow.recommendations.list_orderable(calculation_run_id), key=lambda row: row.id):
                version = recommendation.version
                recommendation.mark_converted_to_order(changed_at=now)
                uow.recommendations.mark_converted(recommendation, expected_version=version)
                groups[(recommendation.supplier_id, recommendation.warehouse_id)].append(recommendation)
            for (supplier_id, warehouse_id), recommendations in sorted(groups.items()):
                order_id = uuid4()
                order = PurchaseOrder(id=order_id, order_number=f"PO-{order_id.hex}",
                                      supplier_id=supplier_id, warehouse_id=warehouse_id,
                                      created_from_run_id=calculation_run_id, created_by=user_id, created_at=now)
                for recommendation in recommendations:
                    order.add_item(PurchaseOrderItem(
                        recommendation_id=recommendation.id, product_id=recommendation.product_id,
                        recommended_quantity=recommendation.recommended_quantity,
                        approved_quantity=recommendation.effective_quantity,
                    ))
                orders.append(uow.orders.add(order))
            if orders:
                uow.commit()
        return tuple(orders)
