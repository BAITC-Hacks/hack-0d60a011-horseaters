from typing import Protocol
from uuid import UUID

from backend.domain.entities.enums import RecommendationStatus, Urgency
from backend.domain.entities.recommendation import Recommendation


class RecommendationRepository(Protocol):
    def get(self, recommendation_id: UUID) -> Recommendation | None: ...

    def list_for_run(
        self,
        run_id: UUID,
        *,
        supplier_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        urgency: Urgency | None = None,
        status: RecommendationStatus | None = None,
        category_id: UUID | None = None,
        sort_by: str = "risk_score",
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Recommendation], int]: ...

    def add_many(self, recommendations: list[Recommendation]) -> None: ...

    def count_for_run(self, run_id: UUID) -> int: ...
