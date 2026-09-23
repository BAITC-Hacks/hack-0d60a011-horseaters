from collections.abc import Collection
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.imports import MonthlySales, SalesTransaction
from backend.domain.enums import TransactionType
from backend.domain.repositories.filters import ALL, IdFilter
from backend.domain.repositories.sales_repository import SalesRepository
from ._read_repository import SqlAlchemyReadRepository, calendar_date, id_filter, time_range, visible_import
from .models.imports import MonthlySalesModel, SalesTransactionModel


class SqlAlchemySalesRepository(SqlAlchemyReadRepository, SalesRepository):
    def list_transactions(
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None, transaction_type: TransactionType | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SalesTransaction]:
        start, end = time_range(start, end)
        model = SalesTransactionModel
        query = select(model).where(
            model.sold_at >= start, model.sold_at < end,
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if product_id is not None:
            query = query.where(model.product_id == product_id)
        if warehouse_id is not None:
            query = query.where(model.warehouse_id == warehouse_id)
        if transaction_type is not None:
            query = query.where(model.transaction_type == transaction_type)
        return self._read(query.order_by(model.sold_at, model.id), SalesTransaction)

    def list_monthly_sales(
        self, start: date, end: date, *, product_id: UUID | None = None,
        warehouse_id: IdFilter = ALL, import_batch_ids: Collection[UUID] | None = None,
    ) -> list[MonthlySales]:
        start, end = calendar_date(start), calendar_date(end)
        if end < start:
            raise ValueError("end must be on or after start")
        model = MonthlySalesModel
        query = select(model).where(
            model.period_start <= end, model.period_end >= start,
            id_filter(model.warehouse_id, warehouse_id),
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if product_id is not None:
            query = query.where(model.product_id == product_id)
        return self._read(query.order_by(model.period_start, model.period_end, model.id), MonthlySales)
