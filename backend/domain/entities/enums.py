from enum import Enum


class StringEnum(str, Enum):
    pass


class CalculationRunStatus(StringEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Urgency(StringEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationStatus(StringEnum):
    SUGGESTED = "suggested"
    ADJUSTED = "adjusted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONVERTED_TO_ORDER = "converted_to_order"


class PurchaseOrderStatus(StringEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXPORTED = "exported"
    CANCELLED = "cancelled"


class ExportFormat(StringEnum):
    XLSX = "xlsx"
    CSV = "csv"
