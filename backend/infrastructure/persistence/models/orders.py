from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, checked_enum
from .enums import ExportFormat, PurchaseOrderStatus


QUANTITY = Numeric(18, 4)
MONEY = Numeric(18, 4)


class RecommendationAdjustmentModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_adjustments"
    __table_args__ = (
        CheckConstraint("new_quantity >= 0", name="nonnegative_new_quantity"),
        Index("ix_recommendation_adjustments_recommendation_changed", "recommendation_id", "changed_at"),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="RESTRICT"), nullable=False
    )
    previous_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    new_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PurchaseOrderModel(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status NOT IN ('approved', 'exported') "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="approved_order_has_audit",
        ),
        Index("ix_purchase_orders_supplier_status_created", "supplier_id", "status", "created_at"),
    )

    order_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_from_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        checked_enum(PurchaseOrderStatus, name="purchase_order_status", length=20),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PurchaseOrderItemModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("approved_quantity > 0", name="positive_approved_quantity"),
        CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="nonnegative_unit_price"),
        CheckConstraint("total_amount IS NULL OR total_amount >= 0", name="nonnegative_total_amount"),
    )

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recommended_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    approved_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(MONEY)
    total_amount: Mapped[Decimal | None] = mapped_column(MONEY)


class OrderExportModel(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "order_exports"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    format: Mapped[ExportFormat] = mapped_column(
        checked_enum(ExportFormat, name="order_export_format", length=20), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
