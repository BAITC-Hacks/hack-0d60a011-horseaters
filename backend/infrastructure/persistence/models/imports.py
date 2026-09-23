from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JSON_DOCUMENT, UUIDPrimaryKeyMixin, checked_enum
from .enums import (
    GrowthSource,
    ImportSourceType,
    ImportStatus,
    MaterialRequirementStatus,
    StockoutSource,
    TransactionType,
    TransitStatus,
)


QUANTITY = Numeric(18, 4)
MONEY = Numeric(18, 4)
FACTOR = Numeric(12, 6)
SCORE = Numeric(5, 4)


class ImportBatchModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        Index("ix_import_batches_imported_by", "imported_by"),
        Index(
            "uq_import_batches_completed_checksum",
            "file_checksum",
            unique=True,
            postgresql_where=text("status = 'completed'"),
            sqlite_where=text("status = 'completed'"),
        ),
    )

    source_type: Mapped[ImportSourceType] = mapped_column(
        checked_enum(ImportSourceType, name="import_source_type", length=50), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        checked_enum(ImportStatus, name="import_status", length=20), nullable=False
    )
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    imported_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT, nullable=True)


class SalesTransactionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sales_transactions"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id", "source_row_number", name="uq_sales_transactions_batch_row"
        ),
        CheckConstraint(
            "(transaction_type = 'sale' AND quantity > 0) "
            "OR (transaction_type = 'return' AND quantity < 0)",
            name="transaction_type_quantity_sign",
        ),
        CheckConstraint(
            "original_transaction_id IS NULL OR transaction_type = 'return'",
            name="original_transaction_only_for_return",
        ),
        CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="nonnegative_unit_price"),
        Index("ix_sales_transactions_product_warehouse_sold", "product_id", "warehouse_id", "sold_at"),
        Index(
            "ix_sales_transactions_customer_sold",
            "anonymous_customer_id",
            "sold_at",
            postgresql_where=text("anonymous_customer_id IS NOT NULL"),
            sqlite_where=text("anonymous_customer_id IS NOT NULL"),
        ),
        Index("ix_sales_transactions_warehouse_id", "warehouse_id"),
        Index("ix_sales_transactions_original_transaction_id", "original_transaction_id"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    external_document_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    anonymous_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(
        checked_enum(TransactionType, name="transaction_type", length=20), nullable=False
    )
    # The referenced row's type is checked by application/domain, not a SQL CHECK.
    original_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_transactions.id", ondelete="RESTRICT"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)


class MonthlySalesModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "monthly_sales"
    __table_args__ = (
        UniqueConstraint("import_batch_id", "source_row_number", name="uq_monthly_sales_batch_row"),
        CheckConstraint("period_end >= period_start", name="valid_period"),
        Index(
            "ix_monthly_sales_product_warehouse_period",
            "product_id", "warehouse_id", "period_start", "period_end",
        ),
        Index("ix_monthly_sales_warehouse_id", "warehouse_id"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)


class InventorySnapshotModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id", "product_id", "warehouse_id", "snapshot_at",
            name="uq_inventory_snapshots_batch_product_warehouse_snapshot",
        ),
        Index(
            "ix_inventory_snapshots_product_warehouse_snapshot",
            "product_id", "warehouse_id", text("snapshot_at DESC"),
        ),
        Index("ix_inventory_snapshots_warehouse_id", "warehouse_id"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity_on_hand: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    quantity_reserved: Mapped[Decimal] = mapped_column(
        QUANTITY, nullable=False, default=Decimal("0"), server_default=text("0")
    )
    quantity_available: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)


class StockoutPeriodModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stockout_periods"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at > started_at", name="valid_period"),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"),
        Index("ix_stockout_periods_import_batch_id", "import_batch_id"),
        Index("ix_stockout_periods_warehouse_id", "warehouse_id"),
        Index(
            "ix_stockout_periods_product_warehouse_period",
            "product_id", "warehouse_id", "started_at", "ended_at",
        ),
    )

    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[StockoutSource] = mapped_column(
        checked_enum(StockoutSource, name="stockout_source", length=20), nullable=False
    )
    confidence: Mapped[Decimal | None] = mapped_column(SCORE, nullable=True)


class InTransitItemModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "in_transit_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        Index("ix_in_transit_items_import_batch_id", "import_batch_id"),
        Index("ix_in_transit_items_supplier_id", "supplier_id"),
        Index("ix_in_transit_items_destination_warehouse_id", "destination_warehouse_id"),
        Index(
            "ix_in_transit_items_product_warehouse_status_expected",
            "product_id", "destination_warehouse_id", "status", "expected_at",
        ),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    external_order_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    destination_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[TransitStatus] = mapped_column(
        checked_enum(TransitStatus, name="transit_status", length=20), nullable=False
    )


class SeasonalityCoefficientModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "seasonality_coefficients"
    __table_args__ = (
        CheckConstraint("month BETWEEN 1 AND 12", name="month_range"),
        CheckConstraint("coefficient > 0", name="positive_coefficient"),
        CheckConstraint(
            "(product_id IS NOT NULL AND category_id IS NULL) "
            "OR (product_id IS NULL AND category_id IS NOT NULL)",
            name="exactly_one_level",
        ),
        Index("ix_seasonality_coefficients_import_batch_id", "import_batch_id"),
        Index("ix_seasonality_coefficients_product_id", "product_id"),
        Index("ix_seasonality_coefficients_category_id", "category_id"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    coefficient: Mapped[Decimal] = mapped_column(FACTOR, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class GrowthAssumptionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "growth_assumptions"
    __table_args__ = (
        CheckConstraint("product_id IS NOT NULL OR category_id IS NOT NULL", name="has_level"),
        Index("ix_growth_assumptions_import_batch_id", "import_batch_id"),
        Index("ix_growth_assumptions_product_id", "product_id"),
        Index("ix_growth_assumptions_category_id", "category_id"),
        Index("ix_growth_assumptions_warehouse_id", "warehouse_id"),
    )

    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    growth_rate: Mapped[Decimal] = mapped_column(FACTOR, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[GrowthSource] = mapped_column(
        checked_enum(GrowthSource, name="growth_source", length=20), nullable=False
    )


class MaterialRequirementModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "material_requirements"
    __table_args__ = (
        CheckConstraint("required_quantity > 0", name="positive_required_quantity"),
        Index("ix_material_requirements_import_batch_id", "import_batch_id"),
        Index("ix_material_requirements_product_id", "product_id"),
        Index("ix_material_requirements_warehouse_id", "warehouse_id"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    external_document_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    required_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    required_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MaterialRequirementStatus] = mapped_column(
        checked_enum(MaterialRequirementStatus, name="material_requirement_status", length=20),
        nullable=False,
    )
