from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.catalog import Supplier, SupplierProduct
from backend.domain.repositories.supplier_repository import SupplierRepository
from ._read_repository import SqlAlchemyReadRepository
from .models.catalog import SupplierModel, SupplierProductModel


class SqlAlchemySupplierRepository(SqlAlchemyReadRepository, SupplierRepository):
    def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        rows = self._read(select(SupplierModel).where(SupplierModel.id == supplier_id), Supplier)
        return rows[0] if rows else None

    def list_terms(
        self, product_id: UUID, *, supplier_id: UUID | None = None, active_only: bool = True,
    ) -> list[SupplierProduct]:
        model = SupplierProductModel
        query = select(model).join(SupplierModel, model.supplier_id == SupplierModel.id).where(
            model.product_id == product_id,
        )
        if supplier_id is not None:
            query = query.where(model.supplier_id == supplier_id)
        if active_only:
            query = query.where(model.is_active.is_(True), SupplierModel.is_active.is_(True))
        return self._read(query.order_by(model.supplier_id, model.id), SupplierProduct)
