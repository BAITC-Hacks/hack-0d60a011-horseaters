from decimal import Decimal
from uuid import UUID

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.domain.entities.recommendation import Recommendation
from backend.domain.repositories.recommendation_repository import (
    RecommendationConflictError, RecommendationNotFoundError,
)


class AdjustRecommendation:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, recommendation_id: UUID, *, expected_version: int,
                new_quantity: Decimal, reason: str, user_id: UUID) -> Recommendation:
        if type(expected_version) is not int or expected_version <= 0:
            raise ValueError("expected_version must be a positive integer")
        with self._uow_factory() as uow:
            recommendation = uow.recommendations.get(recommendation_id)
            if recommendation is None:
                raise RecommendationNotFoundError(f"Recommendation {recommendation_id} was not found")
            if recommendation.version != expected_version:
                raise RecommendationConflictError(f"Recommendation {recommendation_id} has a different version")
            adjustment = recommendation.adjust(new_quantity, reason=reason, changed_by=user_id)
            uow.recommendations.save_adjustment(recommendation, adjustment, expected_version=expected_version)
            uow.commit()
        return recommendation
