from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    DateTime,
    UniqueConstraint,
    Uuid,
    false,
    text,
    true,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, checked_enum
from .enums import UserRole


QUANTITY = Numeric(18, 4)
MONEY = Numeric(18, 4)


class UserModel(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("external_id", name="uq_users_external_id"),)

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        checked_enum(UserRole, name="user_role", length=32), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class UserCredentialModel(Base):
    __tablename__ = "user_credentials"
    __table_args__ = (CheckConstraint("token_version > 0", name="positive_token_version"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CategoryModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("code", name="uq_categories_code"),
        Index("ix_categories_parent_id", "parent_id"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class ProductModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        Index("ix_products_category_id", "category_id"),
    )

    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class WarehouseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("code", name="uq_warehouses_code"),)

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class SupplierModel(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("code", name="uq_suppliers_code"),)

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class SupplierProductModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_products"
    __table_args__ = (
        UniqueConstraint("supplier_id", "product_id", name="uq_supplier_products_supplier_product"),
        CheckConstraint("moq > 0", name="positive_moq"),
        CheckConstraint("package_size > 0", name="positive_package_size"),
        CheckConstraint("lead_time_days >= 0", name="nonnegative_lead_time"),
        CheckConstraint("purchase_price IS NULL OR purchase_price >= 0", name="nonnegative_price"),
        Index("ix_supplier_products_product_id", "product_id"),
        Index(
            "uq_supplier_products_primary_product",
            "product_id",
            unique=True,
            postgresql_where=text("is_active = true AND is_primary = true"),
            sqlite_where=text("is_active = true AND is_primary = true"),
        ),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    moq: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    package_size: Mapped[Decimal] = mapped_column(
        QUANTITY, nullable=False, default=Decimal("1"), server_default=text("1")
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=text("100")
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
