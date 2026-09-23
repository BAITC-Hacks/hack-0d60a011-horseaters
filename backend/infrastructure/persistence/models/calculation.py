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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, JSON_DOCUMENT, TimestampMixin, UUIDPrimaryKeyMixin, checked_enum
from .enums import CalculationRunStatus, RecommendationStatus, Urgency


QUANTITY = Numeric(18, 4)
FACTOR = Numeric(12, 6)
SCORE = Numeric(5, 4)


class CalculationRunModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "calculation_runs"
    __table_args__ = (
        CheckConstraint("forecast_horizon_days > 0", name="positive_forecast_horizon"),
        Index("ix_calculation_runs_status_started_at", "status", "started_at"),
    )

    status: Mapped[CalculationRunStatus] = mapped_column(
        checked_enum(CalculationRunStatus, name="calculation_run_status", length=20),
        nullable=False,
        default=CalculationRunStatus.PENDING,
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    source_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)


class CalculationRunImportModel(Base):
    __tablename__ = "calculation_run_imports"

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_runs.id", ondelete="CASCADE"), primary_key=True
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class DetectedAnomalyModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "detected_anomalies"
    __table_args__ = (
        UniqueConstraint(
            "calculation_run_id",
            "sales_transaction_id",
            "method",
            name="uq_detected_anomalies_run_transaction_method",
        ),
    )

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    original_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    replacement_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    threshold: Mapped[Decimal | None] = mapped_column(QUANTITY)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False, default=dict)


class DemandForecastModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "demand_forecasts"
    __table_args__ = (
        CheckConstraint("forecast_period_end >= forecast_period_start", name="valid_forecast_period"),
        UniqueConstraint(
            "calculation_run_id",
            "product_id",
            "warehouse_id",
            "forecast_period_start",
            "forecast_period_end",
            name="uq_demand_forecasts_run_product_warehouse_period",
        ),
    )

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    forecast_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    raw_demand: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    return_adjustment: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False, default=Decimal("0"))
    anomaly_adjustment: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    stockout_adjustment: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    cleaned_baseline: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    growth_rate: Mapped[Decimal] = mapped_column(FACTOR, nullable=False)
    seasonality_index: Mapped[Decimal] = mapped_column(FACTOR, nullable=False)
    forecast_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False, default=dict)


class RecommendationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint("recommended_quantity >= 0", name="nonnegative_recommended_quantity"),
        CheckConstraint("effective_quantity >= 0", name="nonnegative_effective_quantity"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="risk_score_range"),
        CheckConstraint("version > 0", name="positive_version"),
        UniqueConstraint(
            "calculation_run_id",
            "product_id",
            "warehouse_id",
            "supplier_id",
            name="uq_recommendations_run_product_warehouse_supplier",
        ),
        Index(
            "ix_recommendations_run_product_warehouse",
            "calculation_run_id",
            "product_id",
            "warehouse_id",
        ),
        Index(
            "ix_recommendations_run_supplier_urgency",
            "calculation_run_id",
            "supplier_id",
            "urgency",
        ),
        Index(
            "ix_recommendations_run_warehouse_status",
            "calculation_run_id",
            "warehouse_id",
            "status",
        ),
    )

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    forecast_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    current_stock: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    in_transit_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    material_requirement_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    safety_stock: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    shortage_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    quantity_before_rounding: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    moq: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    package_size: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    recommended_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    effective_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(SCORE, nullable=False)
    urgency: Mapped[Urgency] = mapped_column(
        checked_enum(Urgency, name="recommendation_urgency", length=20), nullable=False
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        checked_enum(RecommendationStatus, name="recommendation_status", length=30),
        nullable=False,
        default=RecommendationStatus.SUGGESTED,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_details: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
