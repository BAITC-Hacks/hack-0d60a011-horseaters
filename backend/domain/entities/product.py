from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ._validation import aware_datetime
from .base import Entity, utc_now


@dataclass(frozen=True, kw_only=True)
class Product(Entity):
    sku: str
    name: str
    unit: str
    category_id: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        aware_datetime(self.created_at, "created_at")
        aware_datetime(self.updated_at, "updated_at")
