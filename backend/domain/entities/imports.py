"""Imported facts and assumptions as plain Python domain entities."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from backend.domain.enums import (
    GrowthSource,
    ImportSourceType,
    ImportStatus,
    MaterialRequirementStatus,
    StockoutSource,
    TransactionType,
    TransitStatus,
)

from ._validation import (
    aware_datetime,
    calendar_date,
    decimal_value,
    enum_value,
    positive_decimal,
)
from .base import Entity


@dataclass(frozen=True, kw_only=True)
class ImportBatch(Entity):
    source_type: ImportSourceType
    file_name: str
    file_checksum: str
    status: ImportStatus
    imported_by: UUID
    imported_at: datetime
    row_count: int = 0
    error_details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        enum_value(self.source_type, ImportSourceType, "source_type")
        enum_value(self.status, ImportStatus, "status")
        aware_datetime(self.imported_at, "imported_at")


@dataclass(frozen=True, kw_only=True)
class SalesTransaction(Entity):
    import_batch_id: UUID
    source_row_number: int
    sold_at: datetime
    product_id: UUID
    warehouse_id: UUID
    transaction_type: TransactionType
    quantity: Decimal
    external_document_number: str | None = None
    anonymous_customer_id: str | None = None
    original_transaction_id: UUID | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None

    def __post_init__(self) -> None:
        enum_value(self.transaction_type, TransactionType, "transaction_type")
        aware_datetime(self.sold_at, "sold_at")
        decimal_value(self.quantity, "quantity")
        if self.transaction_type is TransactionType.SALE:
            if self.quantity <= 0:
                raise ValueError("A sale must have quantity > 0")
            if self.original_transaction_id is not None:
                raise ValueError("Only returns may reference an original transaction")
        elif self.quantity >= 0:
            raise ValueError("A return must have quantity < 0")
        if self.unit_price is not None:
            decimal_value(self.unit_price, "unit_price", minimum=Decimal("0"))
        if self.total_amount is not None:
            decimal_value(self.total_amount, "total_amount")


@dataclass(frozen=True, kw_only=True)
class MonthlySales(Entity):
    import_batch_id: UUID
    source_row_number: int
    product_id: UUID
    period_start: date
    period_end: date
    quantity: Decimal
    warehouse_id: UUID | None = None

    def __post_init__(self) -> None:
        calendar_date(self.period_start, "period_start")
        calendar_date(self.period_end, "period_end")
        if self.period_end < self.period_start:
            raise ValueError("period_end must be >= period_start")
        decimal_value(self.quantity, "quantity")


@dataclass(frozen=True, kw_only=True)
class InventorySnapshot(Entity):
    import_batch_id: UUID
    product_id: UUID
    warehouse_id: UUID
    snapshot_at: datetime
    quantity_on_hand: Decimal
    quantity_available: Decimal
    quantity_reserved: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        aware_datetime(self.snapshot_at, "snapshot_at")
        decimal_value(self.quantity_on_hand, "quantity_on_hand")
        decimal_value(self.quantity_available, "quantity_available")
        decimal_value(self.quantity_reserved, "quantity_reserved")


@dataclass(frozen=True, kw_only=True)
class StockoutPeriod(Entity):
    product_id: UUID
    warehouse_id: UUID
    started_at: datetime
    source: StockoutSource
    import_batch_id: UUID | None = None
    ended_at: datetime | None = None
    confidence: Decimal | None = None

    def __post_init__(self) -> None:
        enum_value(self.source, StockoutSource, "source")
        aware_datetime(self.started_at, "started_at")
        if self.ended_at is not None:
            aware_datetime(self.ended_at, "ended_at")
            if self.ended_at <= self.started_at:
                raise ValueError("ended_at must be > started_at")
        if self.confidence is not None:
            decimal_value(self.confidence, "confidence", minimum=Decimal("0"))
            if self.confidence > 1:
                raise ValueError("confidence must be <= 1")


@dataclass(frozen=True, kw_only=True)
class InTransitItem(Entity):
    import_batch_id: UUID
    supplier_id: UUID
    product_id: UUID
    destination_warehouse_id: UUID
    quantity: Decimal
    status: TransitStatus
    external_order_number: str | None = None
    expected_at: datetime | None = None

    def __post_init__(self) -> None:
        enum_value(self.status, TransitStatus, "status")
        positive_decimal(self.quantity, "quantity")
        if self.expected_at is not None:
            aware_datetime(self.expected_at, "expected_at")


@dataclass(frozen=True, kw_only=True)
class SeasonalityCoefficient(Entity):
    import_batch_id: UUID
    month: int
    coefficient: Decimal
    valid_from: date
    version: int
    product_id: UUID | None = None
    category_id: UUID | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError("month must be between 1 and 12")
        positive_decimal(self.coefficient, "coefficient")
        if (self.product_id is None) == (self.category_id is None):
            raise ValueError("Exactly one of product_id and category_id is required")
        calendar_date(self.valid_from, "valid_from")
        if self.valid_to is not None:
            calendar_date(self.valid_to, "valid_to")


@dataclass(frozen=True, kw_only=True)
class GrowthAssumption(Entity):
    growth_rate: Decimal
    valid_from: date
    source: GrowthSource
    import_batch_id: UUID | None = None
    product_id: UUID | None = None
    category_id: UUID | None = None
    warehouse_id: UUID | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        enum_value(self.source, GrowthSource, "source")
        decimal_value(self.growth_rate, "growth_rate")
        if self.product_id is None and self.category_id is None:
            raise ValueError("product_id or category_id is required")
        calendar_date(self.valid_from, "valid_from")
        if self.valid_to is not None:
            calendar_date(self.valid_to, "valid_to")


@dataclass(frozen=True, kw_only=True)
class MaterialRequirement(Entity):
    import_batch_id: UUID
    product_id: UUID
    warehouse_id: UUID
    required_quantity: Decimal
    required_at: datetime
    status: MaterialRequirementStatus
    external_document_number: str | None = None

    def __post_init__(self) -> None:
        enum_value(self.status, MaterialRequirementStatus, "status")
        positive_decimal(self.required_quantity, "required_quantity")
        aware_datetime(self.required_at, "required_at")
