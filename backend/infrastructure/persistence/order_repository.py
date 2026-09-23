from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.domain.entities.enums import PurchaseOrderStatus
from backend.domain.entities.order_export import OrderExport
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.repositories.order_repository import (
    DuplicateOrderNumberError,
    InvalidOrderPersistenceStateError,
    OrderNotFoundError,
    OrderConflictError,
    RecommendationAlreadyOrderedError,
)
from backend.infrastructure.persistence.models.orders import (
    OrderExportModel,
    PurchaseOrderItemModel,
    PurchaseOrderModel,
)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class SqlAlchemyOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, order_id: UUID) -> PurchaseOrder | None:
        model = self._session.get(PurchaseOrderModel, order_id)
        return self._to_domain(model) if model is not None else None

    def get_by_number(self, order_number: str) -> PurchaseOrder | None:
        model = self._session.scalar(
            select(PurchaseOrderModel)
            .where(PurchaseOrderModel.order_number == order_number)
            .limit(1)
        )
        return self._to_domain(model) if model is not None else None

    def list_by_supplier(
        self,
        supplier_id: UUID,
        *,
        status: PurchaseOrderStatus | None = None,
    ) -> Sequence[PurchaseOrder]:
        statement = select(PurchaseOrderModel).where(
            PurchaseOrderModel.supplier_id == supplier_id
        )
        if status is not None:
            statement = statement.where(PurchaseOrderModel.status == status)
        models = self._session.scalars(
            statement.order_by(PurchaseOrderModel.created_at.desc())
        ).all()
        return tuple(self._to_domain(model) for model in models)

    def add(self, order: PurchaseOrder) -> PurchaseOrder:
        if order.status is not PurchaseOrderStatus.DRAFT:
            raise InvalidOrderPersistenceStateError(
                "a purchase order must be persisted as draft before approval"
            )
        if self.get_by_number(order.order_number) is not None:
            raise DuplicateOrderNumberError(order.order_number)
        self._ensure_recommendations_available(order.items)

        self._session.add(
            PurchaseOrderModel(
                id=order.id,
                order_number=order.order_number,
                supplier_id=order.supplier_id,
                warehouse_id=order.warehouse_id,
                created_from_run_id=order.created_from_run_id,
                status=order.status,
                created_by=order.created_by,
                created_at=order.created_at,
                approved_by=order.approved_by,
                approved_at=order.approved_at,
                exported_at=order.exported_at,
            )
        )
        # No ORM relationships: flush the FK parent explicitly before its items.
        self._session.flush()
        self._session.add_all(
            PurchaseOrderItemModel(
                id=item.id,
                purchase_order_id=order.id,
                recommendation_id=item.recommendation_id,
                product_id=item.product_id,
                recommended_quantity=item.recommended_quantity,
                approved_quantity=item.approved_quantity,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
            )
            for item in order.items
        )
        self._session.flush()
        return self._require_domain(order.id)

    def save(self, order: PurchaseOrder, *, expected_status: PurchaseOrderStatus | None = None) -> PurchaseOrder:
        model = self._require(order.id)
        if expected_status is not None and model.status is not expected_status:
            raise OrderConflictError(f"Purchase order {order.id} changed concurrently")
        self._validate_transition(model.status, order.status)
        self._validate_immutable_header(model, order)
        self._validate_immutable_items(model.id, order.items)

        if model.status is not PurchaseOrderStatus.DRAFT and (
            model.approved_by != order.approved_by or
            (_aware(model.approved_at) if model.approved_at else None) != order.approved_at or
            (_aware(model.exported_at) if model.exported_at else None) != order.exported_at
        ):
            raise OrderConflictError("approval and export audit cannot be overwritten")
        self._change_status(order.id, model.status, status=order.status,
                            approved_by=order.approved_by, approved_at=order.approved_at,
                            exported_at=order.exported_at)
        return self._require_domain(order.id)

    def add_export(self, export: OrderExport) -> OrderExport:
        order = self._require(export.purchase_order_id)
        if order.status is not PurchaseOrderStatus.APPROVED:
            raise InvalidOrderPersistenceStateError(
                "only an approved purchase order can be exported"
            )
        domain_order = self._to_domain(order)
        domain_order.mark_exported(exported_at=export.created_at)
        self._change_status(order.id, PurchaseOrderStatus.APPROVED,
                            status=domain_order.status, exported_at=domain_order.exported_at)
        model = OrderExportModel(
            id=export.id,
            purchase_order_id=export.purchase_order_id,
            format=export.format,
            file_name=export.file_name,
            file_checksum=export.file_checksum,
            created_by=export.created_by,
            created_at=export.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return self._export_to_domain(model)

    def _change_status(self, order_id: UUID, expected_status: PurchaseOrderStatus, **values) -> None:
        result = self._session.execute(update(PurchaseOrderModel).where(
            PurchaseOrderModel.id == order_id,
            PurchaseOrderModel.status == expected_status,
        ).values(**values).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise OrderConflictError(f"Purchase order {order_id} changed concurrently")
        self._session.expire_all()

    def list_exports(self, order_id: UUID) -> Sequence[OrderExport]:
        self._require(order_id)
        models = self._session.scalars(
            select(OrderExportModel)
            .where(OrderExportModel.purchase_order_id == order_id)
            .order_by(OrderExportModel.created_at, OrderExportModel.id)
        ).all()
        return tuple(self._export_to_domain(model) for model in models)

    def _require(self, order_id: UUID) -> PurchaseOrderModel:
        model = self._session.get(PurchaseOrderModel, order_id)
        if model is None:
            raise OrderNotFoundError(order_id)
        return model

    def _require_domain(self, order_id: UUID) -> PurchaseOrder:
        return self._to_domain(self._require(order_id))

    def _to_domain(self, model: PurchaseOrderModel) -> PurchaseOrder:
        item_models = self._session.scalars(
            select(PurchaseOrderItemModel)
            .where(PurchaseOrderItemModel.purchase_order_id == model.id)
            .order_by(PurchaseOrderItemModel.id)
        ).all()
        return PurchaseOrder(
            id=model.id,
            order_number=model.order_number,
            supplier_id=model.supplier_id,
            warehouse_id=model.warehouse_id,
            created_from_run_id=model.created_from_run_id,
            status=model.status,
            created_by=model.created_by,
            created_at=_aware(model.created_at),
            approved_by=model.approved_by,
            approved_at=_aware(model.approved_at) if model.approved_at is not None else None,
            exported_at=_aware(model.exported_at) if model.exported_at is not None else None,
            items=[self._item_to_domain(item) for item in item_models],
        )

    def _ensure_recommendations_available(
        self, items: Sequence[PurchaseOrderItem]
    ) -> None:
        recommendation_ids = [item.recommendation_id for item in items]
        if len(recommendation_ids) != len(set(recommendation_ids)):
            duplicate = next(
                item_id
                for item_id in recommendation_ids
                if recommendation_ids.count(item_id) > 1
            )
            raise RecommendationAlreadyOrderedError(duplicate)
        if not recommendation_ids:
            return
        existing = self._session.scalar(
            select(PurchaseOrderItemModel.recommendation_id)
            .where(PurchaseOrderItemModel.recommendation_id.in_(recommendation_ids))
            .limit(1)
        )
        if existing is not None:
            raise RecommendationAlreadyOrderedError(existing)

    def _validate_immutable_items(
        self,
        order_id: UUID,
        items: Sequence[PurchaseOrderItem],
    ) -> None:
        stored = self._session.scalars(
            select(PurchaseOrderItemModel).where(
                PurchaseOrderItemModel.purchase_order_id == order_id
            )
        ).all()
        stored_values = {
            (
                item.id,
                item.recommendation_id,
                item.product_id,
                item.recommended_quantity,
                item.approved_quantity,
                item.unit_price,
                item.total_amount,
            )
            for item in stored
        }
        domain_values = {
            (
                item.id,
                item.recommendation_id,
                item.product_id,
                item.recommended_quantity,
                item.approved_quantity,
                item.unit_price,
                item.total_amount,
            )
            for item in items
        }
        if stored_values != domain_values:
            raise InvalidOrderPersistenceStateError(
                "persisted purchase order items are immutable"
            )

    @staticmethod
    def _validate_immutable_header(
        model: PurchaseOrderModel, order: PurchaseOrder
    ) -> None:
        if (
            model.order_number != order.order_number
            or model.supplier_id != order.supplier_id
            or model.warehouse_id != order.warehouse_id
            or model.created_from_run_id != order.created_from_run_id
            or model.created_by != order.created_by
        ):
            raise InvalidOrderPersistenceStateError(
                "persisted purchase order header is immutable"
            )

    @staticmethod
    def _validate_transition(
        current: PurchaseOrderStatus, target: PurchaseOrderStatus
    ) -> None:
        allowed = {
            PurchaseOrderStatus.DRAFT: {
                PurchaseOrderStatus.DRAFT,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.CANCELLED,
            },
            PurchaseOrderStatus.APPROVED: {
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.CANCELLED,
            },
            PurchaseOrderStatus.EXPORTED: {PurchaseOrderStatus.EXPORTED},
            PurchaseOrderStatus.CANCELLED: {PurchaseOrderStatus.CANCELLED},
        }
        if target not in allowed[current]:
            raise InvalidOrderPersistenceStateError(
                f"invalid purchase order transition: {current.value} -> {target.value}"
            )
        if target is PurchaseOrderStatus.EXPORTED and current is not target:
            raise InvalidOrderPersistenceStateError(
                "an export must be recorded through add_export"
            )

    @staticmethod
    def _item_to_domain(model: PurchaseOrderItemModel) -> PurchaseOrderItem:
        return PurchaseOrderItem(
            id=model.id,
            recommendation_id=model.recommendation_id,
            product_id=model.product_id,
            recommended_quantity=model.recommended_quantity,
            approved_quantity=model.approved_quantity,
            unit_price=model.unit_price,
            total_amount=model.total_amount,
        )

    @staticmethod
    def _export_to_domain(model: OrderExportModel) -> OrderExport:
        return OrderExport(
            id=model.id,
            purchase_order_id=model.purchase_order_id,
            format=model.format,
            file_name=model.file_name,
            file_checksum=model.file_checksum,
            created_by=model.created_by,
            created_at=_aware(model.created_at),
        )
