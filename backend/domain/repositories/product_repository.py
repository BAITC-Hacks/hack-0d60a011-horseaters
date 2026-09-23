from typing import Protocol
from uuid import UUID

from backend.domain.entities.product import Product
from .filters import ALL, IdFilter


class ProductRepository(Protocol):
    def get_by_id(self, product_id: UUID) -> Product | None: ...

    def get_by_sku(self, sku: str) -> Product | None: ...

    def list_products(
        self, *, category_id: IdFilter = ALL, is_active: bool | None = True,
    ) -> list[Product]:
        """None category selects uncategorized products; ALL disables that filter."""
        ...
