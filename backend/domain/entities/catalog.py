"""Catalog entities. Changes are represented with dataclasses.replace()."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from backend.domain.enums import UserRole

from ._validation import aware_datetime, decimal_value, enum_value, positive_decimal
from .base import Entity, utc_now


@dataclass(frozen=True, kw_only=True)
class User(Entity):
    external_id: str
    display_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        enum_value(self.role, UserRole, "role")
        aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, kw_only=True)
class Category(Entity):
    code: str
    name: str
    parent_id: UUID | None = None
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class Warehouse(Entity):
    code: str
    name: str
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class Supplier(Entity):
    code: str
    name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, kw_only=True)
class SupplierProduct(Entity):
    supplier_id: UUID
    product_id: UUID
    moq: Decimal
    lead_time_days: int
    package_size: Decimal = Decimal("1")
    purchase_price: Decimal | None = None
    currency: str | None = None
    priority: int = 100
    is_primary: bool = False
    is_active: bool = True

    def __post_init__(self) -> None:
        positive_decimal(self.moq, "moq")
        positive_decimal(self.package_size, "package_size")
        if self.lead_time_days < 0:
            raise ValueError("lead_time_days must be >= 0")
        if self.purchase_price is not None:
            decimal_value(self.purchase_price, "purchase_price", minimum=Decimal("0"))
