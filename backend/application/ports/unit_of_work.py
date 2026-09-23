from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from backend.domain.repositories.import_repository import ImportRepository
from backend.domain.repositories.inventory_repository import InventoryRepository
from backend.domain.repositories.material_requirement_repository import MaterialRequirementRepository
from backend.domain.repositories.product_repository import ProductRepository
from backend.domain.repositories.sales_repository import SalesRepository
from backend.domain.repositories.seasonality_repository import SeasonalityRepository
from backend.domain.repositories.supplier_repository import SupplierRepository


class Repository(Protocol):
    """Marker port refined by repository-specific protocols in REP tasks."""


class UnitOfWork(Protocol):
    """Application transaction boundary; contains no SQLAlchemy dependency."""

    @property
    def imports(self) -> ImportRepository: ...

    @property
    def sales(self) -> SalesRepository: ...

    @property
    def inventory(self) -> InventoryRepository: ...

    @property
    def suppliers(self) -> SupplierRepository: ...

    @property
    def products(self) -> ProductRepository: ...

    @property
    def seasonality(self) -> SeasonalityRepository: ...

    @property
    def material_requirements(self) -> MaterialRequirementRepository: ...

    @property
    def calculation_runs(self) -> Repository: ...

    @property
    def recommendations(self) -> Repository: ...

    @property
    def orders(self) -> Repository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
