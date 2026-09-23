from enum import Enum

from backend.domain.entities.enums import (
    CalculationRunStatus,
    ExportFormat,
    PurchaseOrderStatus,
    RecommendationStatus,
    Urgency,
)


class StringEnum(str, Enum):
    pass


class UserRole(StringEnum):
    BUYER = "buyer"
    ADMIN = "admin"
    VIEWER = "viewer"


class ImportSourceType(StringEnum):
    SALES = "sales"
    MONTHLY_SALES = "monthly_sales"
    INVENTORY = "inventory"
    STOCKOUT = "stockout"
    IN_TRANSIT = "in_transit"
    SEASONALITY = "seasonality"
    SUPPLIER_TERMS = "supplier_terms"
    GROWTH = "growth"
    MATERIAL_REQUIREMENTS = "material_requirements"


class ImportStatus(StringEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionType(StringEnum):
    SALE = "sale"
    RETURN = "return"


class StockoutSource(StringEnum):
    IMPORTED = "imported"
    INFERRED = "inferred"
    MANUAL = "manual"


class TransitStatus(StringEnum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class GrowthSource(StringEnum):
    CALCULATED = "calculated"
    IMPORTED = "imported"
    MANUAL = "manual"


class MaterialRequirementStatus(StringEnum):
    PLANNED = "planned"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


__all__ = [
    "CalculationRunStatus",
    "ExportFormat",
    "GrowthSource",
    "ImportSourceType",
    "ImportStatus",
    "MaterialRequirementStatus",
    "PurchaseOrderStatus",
    "RecommendationStatus",
    "StockoutSource",
    "TransactionType",
    "TransitStatus",
    "Urgency",
    "UserRole",
]
