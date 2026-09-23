from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectedAnomaly:
    calculation_run_id: UUID
    sales_transaction_id: UUID
    method: str
    original_quantity: Decimal
    replacement_quantity: Decimal
    reason: str
    threshold: Decimal | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise ValueError("anomaly method must not be empty")
        if not self.reason.strip():
            raise ValueError("anomaly reason must not be empty")
        if self.original_quantity < 0:
            raise ValueError("original_quantity must be nonnegative")
        if self.replacement_quantity < 0:
            raise ValueError("replacement_quantity must be nonnegative")
        if self.threshold is not None and self.threshold < 0:
            raise ValueError("threshold must be nonnegative")
