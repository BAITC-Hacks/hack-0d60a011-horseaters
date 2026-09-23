from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from .enums import CalculationRunStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must contain timezone information")


@dataclass(slots=True, kw_only=True)
class CalculationRun:
    started_by: UUID
    forecast_horizon_days: int
    source_cutoff_at: datetime
    algorithm_version: str
    parameters: Mapping[str, Any]
    warehouse_id: UUID | None = None
    category_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    status: CalculationRunStatus = CalculationRunStatus.PENDING
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    error_details: Mapping[str, Any] | None = None
    import_batch_ids: set[UUID] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.forecast_horizon_days <= 0:
            raise ValueError("forecast_horizon_days must be positive")
        if not self.algorithm_version.strip():
            raise ValueError("algorithm_version must not be empty")
        require_aware(self.source_cutoff_at, "source_cutoff_at")
        require_aware(self.started_at, "started_at")
        if self.finished_at is not None:
            require_aware(self.finished_at, "finished_at")
            if self.finished_at < self.started_at:
                raise ValueError("finished_at cannot be earlier than started_at")
        if self.status in {CalculationRunStatus.COMPLETED, CalculationRunStatus.FAILED}:
            if self.finished_at is None:
                raise ValueError("finished run must have finished_at")

    def attach_import(self, import_batch_id: UUID) -> None:
        if self.status is not CalculationRunStatus.PENDING:
            raise ValueError("imports can only be attached to a pending calculation run")
        self.import_batch_ids.add(import_batch_id)

    def start(self) -> None:
        if self.status is not CalculationRunStatus.PENDING:
            raise ValueError("only a pending calculation run can be started")
        if not self.import_batch_ids:
            raise ValueError("calculation run must reference at least one import batch")
        self.status = CalculationRunStatus.RUNNING

    def complete(self, *, finished_at: datetime | None = None) -> None:
        if self.status is not CalculationRunStatus.RUNNING:
            raise ValueError("only a running calculation can be completed")
        completed_at = finished_at or utc_now()
        require_aware(completed_at, "finished_at")
        if completed_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        self.status = CalculationRunStatus.COMPLETED
        self.finished_at = completed_at
        self.error_details = None

    def fail(
        self,
        error_details: Mapping[str, Any],
        *,
        finished_at: datetime | None = None,
    ) -> None:
        if self.status not in {CalculationRunStatus.PENDING, CalculationRunStatus.RUNNING}:
            raise ValueError("completed or failed calculation cannot fail again")
        failed_at = finished_at or utc_now()
        require_aware(failed_at, "finished_at")
        if failed_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        self.status = CalculationRunStatus.FAILED
        self.finished_at = failed_at
        self.error_details = dict(error_details)
