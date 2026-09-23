from __future__ import annotations

from datetime import datetime, timezone

from backend.application.dto.calculation import RunCalculationCommand
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.application.services.calculation_pipeline import CalculationPipeline
from backend.domain.entities.calculation_run import CalculationRun
from backend.domain.value_objects.demand import DemandSource


class RunCalculation:
    def __init__(
        self, uow_factory: UnitOfWorkFactory,
        pipeline: CalculationPipeline | None = None,
        *, algorithm_version: str = "mvp-2",
    ) -> None:
        self._uow_factory = uow_factory
        self._pipeline = pipeline or CalculationPipeline()
        self._algorithm_version = algorithm_version

    def execute(self, command: RunCalculationCommand) -> CalculationRun:
        if not isinstance(command.demand_source, DemandSource):
            raise ValueError("demand_source must be explicit and supported")
        if command.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        run = CalculationRun(
            started_by=command.user_id,
            forecast_horizon_days=command.horizon_days,
            source_cutoff_at=datetime.now(timezone.utc),
            algorithm_version=self._algorithm_version,
            parameters={"horizon_days": command.horizon_days,
                        "demand_source": command.demand_source.value,
                        "warehouse_id": str(command.warehouse_id) if command.warehouse_id else None,
                        "category_id": str(command.category_id) if command.category_id else None,
                        **(self._pipeline.configuration() if isinstance(self._pipeline, CalculationPipeline) else {})},
            warehouse_id=command.warehouse_id,
            category_id=command.category_id,
        )
        with self._uow_factory() as uow:
            for batch in uow.imports.list_completed():
                if batch.imported_at <= run.source_cutoff_at:
                    run.attach_import(batch.id)
            if not run.import_batch_ids:
                run.fail({"error_type": "MissingImports", "message": "no completed import batches available"})
                uow.calculation_runs.add(run)
                uow.commit()
                return run
            run.start()
            uow.calculation_runs.add(run)
            uow.commit()

        try:
            with self._uow_factory() as uow:
                results = self._pipeline.calculate(run, uow)
                uow.calculation_runs.add_results(results.forecasts, results.anomalies)
                uow.recommendations.add_many(results.recommendations)
                run.complete()
                uow.calculation_runs.save(run)
                uow.commit()
        except Exception as error:
            try:
                with self._uow_factory() as uow:
                    persisted = uow.calculation_runs.get(run.id)
                    if persisted is None:
                        raise LookupError(f"calculation run {run.id} disappeared")
                    persisted.fail({"error_type": type(error).__name__, "message": str(error)})
                    uow.calculation_runs.save(persisted)
                    uow.commit()
            except Exception as persistence_error:
                error.add_note(
                    "Failed to persist calculation failure: "
                    f"{type(persistence_error).__name__}: {persistence_error}"
                )
            raise
        return run
