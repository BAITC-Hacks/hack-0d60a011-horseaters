from collections.abc import Collection
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.domain.entities.imports import MaterialRequirement
from backend.domain.enums import MaterialRequirementStatus


class MaterialRequirementRepository(Protocol):
    def list_requirements(
        self, start: datetime, end: datetime, *, product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        status: MaterialRequirementStatus | None = MaterialRequirementStatus.PLANNED,
        import_batch_ids: Collection[UUID] | None = None,
    ) -> list[MaterialRequirement]:
        """required_at in [start, end); explicit status, None means all statuses."""
        ...
