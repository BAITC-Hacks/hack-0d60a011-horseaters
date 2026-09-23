from uuid import UUID

from backend.application.dto.calculation import CalculationRunResult
from backend.application.ports.unit_of_work import UnitOfWorkFactory


class GetCalculationRun:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, run_id: UUID) -> CalculationRunResult | None:
        with self._uow_factory() as uow:
            run = uow.calculation_runs.get(run_id)
            if run is None:
                return None
            count = uow.recommendations.count_for_run(run_id)
            return CalculationRunResult(
                id=run.id, status=run.status, parameters=run.parameters,
                started_at=run.started_at, finished_at=run.finished_at,
                algorithm_version=run.algorithm_version,
                error_details=run.error_details, recommendation_count=count,
                import_batch_ids=tuple(sorted(run.import_batch_ids)),
            )
