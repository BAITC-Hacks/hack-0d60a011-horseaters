from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.entities.enums import CalculationRunStatus


class CalculationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    warehouse_id: UUID | None = None
    category_id: UUID | None = None
    horizon_days: int = Field(gt=0)


class CalculationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: CalculationRunStatus
    parameters: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None
    algorithm_version: str
    error_details: dict[str, Any] | None
    recommendation_count: int = Field(ge=0)
    import_batch_ids: list[UUID]
