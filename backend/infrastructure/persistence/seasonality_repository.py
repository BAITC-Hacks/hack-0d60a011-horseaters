from collections.abc import Collection
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select

from backend.domain.entities.imports import GrowthAssumption, SeasonalityCoefficient
from backend.domain.enums import GrowthSource
from backend.domain.repositories.filters import ALL, AmbiguousSourceDataError, IdFilter
from backend.domain.repositories.seasonality_repository import SeasonalityRepository
from ._read_repository import SqlAlchemyReadRepository, calendar_date, id_filter, visible_import
from .models.catalog import ProductModel
from .models.imports import GrowthAssumptionModel, SeasonalityCoefficientModel


class SqlAlchemySeasonalityRepository(SqlAlchemyReadRepository, SeasonalityRepository):
    def list_coefficients(
        self, product_id: UUID, on_date: date, *, version: int | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[SeasonalityCoefficient]:
        on_date = calendar_date(on_date)
        model = SeasonalityCoefficientModel
        category = select(ProductModel.category_id).where(ProductModel.id == product_id).scalar_subquery()
        query = select(model).where(
            or_(model.product_id == product_id, model.category_id == category),
            model.month == on_date.month, model.valid_from <= on_date,
            or_(model.valid_to.is_(None), model.valid_to >= on_date),
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if version is not None:
            query = query.where(model.version == version)
        rows = self._read(query.order_by(model.id), SeasonalityCoefficient)
        product_rows = [row for row in rows if row.product_id == product_id]
        return product_rows or rows

    def get_coefficient(
        self, product_id: UUID, on_date: date, *, version: int | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> SeasonalityCoefficient | None:
        rows = self.list_coefficients(product_id, on_date, version=version, import_batch_ids=import_batch_ids)
        if len(rows) > 1:
            raise AmbiguousSourceDataError("Multiple seasonality coefficients; specify version/import_batch_ids")
        return rows[0] if rows else None

    def list_growth_assumptions(
        self, on_date: date, *, product_id: IdFilter = ALL, category_id: IdFilter = ALL,
        warehouse_id: IdFilter = ALL, source: GrowthSource | None = None,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[GrowthAssumption]:
        on_date = calendar_date(on_date)
        model = GrowthAssumptionModel
        query = select(model).where(
            id_filter(model.product_id, product_id), id_filter(model.category_id, category_id),
            id_filter(model.warehouse_id, warehouse_id), model.valid_from <= on_date,
            or_(model.valid_to.is_(None), model.valid_to >= on_date),
            visible_import(model.import_batch_id, import_batch_ids),
        )
        if source is not None:
            query = query.where(model.source == source)
        return self._read(query.order_by(model.valid_from, model.id), GrowthAssumption)
