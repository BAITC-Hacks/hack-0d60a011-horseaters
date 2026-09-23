from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.infrastructure.persistence.database import Database
from backend.infrastructure.persistence.application_uow import create_application_uow_factory
from backend.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from backend.application.use_cases.adjust_recommendation import AdjustRecommendation
from backend.application.use_cases.approve_order import ApproveOrder
from backend.application.use_cases.create_orders import CreateOrders
from backend.application.use_cases.download_order_export import DownloadOrderExport
from backend.application.use_cases.explain_recommendation import ExplainRecommendation
from backend.application.use_cases.export_order import ExportOrder
from backend.application.use_cases.get_calculation_run import GetCalculationRun
from backend.application.use_cases.get_import_status import GetImportStatus
from backend.application.use_cases.get_order import GetOrder
from backend.application.use_cases.import_data import ImportData
from backend.application.use_cases.import_file import ImportFileUseCase
from backend.application.use_cases.list_recommendations import ListRecommendations
from backend.application.use_cases.run_calculation import RunCalculation
from backend.domain.entities.catalog import User
from backend.domain.enums import UserRole
from backend.infrastructure.excel.artifact_store import FileExportArtifactStore
from backend.infrastructure.excel.exporter import XlsxOrderExporter
from backend.infrastructure.excel.readers import ExcelImportReader
from backend.infrastructure.persistence.import_gateway import SqlAlchemyImportGateway


def get_db(request: Request) -> Iterator[Session]:
    """Provide one transaction per request through FastAPI Depends(get_db)."""
    database: Database = request.app.state.database
    with database.session() as session:
        yield session


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    """Inject a factory: a use case may need multiple transaction boundaries."""
    database: Database = request.app.state.database
    return create_application_uow_factory(database)


def get_uow(request: Request) -> Iterator[UnitOfWork]:
    """One uncommitted UoW for read-only or single-transaction endpoints."""
    with get_uow_factory(request)() as uow:
        yield uow


def get_current_user(request: Request) -> User:
    """Trusted authentication middleware sets state.user; HTTP headers/body cannot do so."""
    user = getattr(request.state, "user", None)
    if not isinstance(user, User) or not user.is_active:
        raise HTTPException(403, detail={"code": "forbidden"})
    return user


def require_writer(user: User = Depends(get_current_user)) -> User:
    if not user.is_active or user.role not in (UserRole.BUYER, UserRole.ADMIN):
        raise HTTPException(403, detail={"code": "forbidden"})
    return user


def get_import_data(request: Request) -> ImportData:
    return ImportData(ImportFileUseCase(ExcelImportReader(), SqlAlchemyImportGateway(request.app.state.database.session_factory)))


def get_import_status(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> GetImportStatus:
    return GetImportStatus(factory)


def get_run_calculation(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> RunCalculation:
    return RunCalculation(factory)


def get_calculation_run(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> GetCalculationRun:
    return GetCalculationRun(factory)


def get_list_recommendations(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> ListRecommendations:
    return ListRecommendations(factory)


def get_explain_recommendation(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> ExplainRecommendation:
    return ExplainRecommendation(factory)


def get_adjust_recommendation(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> AdjustRecommendation:
    return AdjustRecommendation(factory)


def get_create_orders(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> CreateOrders:
    return CreateOrders(factory)


def get_order(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> GetOrder:
    return GetOrder(factory)


def get_approve_order(factory: UnitOfWorkFactory = Depends(get_uow_factory)) -> ApproveOrder:
    return ApproveOrder(factory)


def get_artifact_store(request: Request) -> FileExportArtifactStore:
    return request.app.state.export_artifacts


def get_export_order(factory: UnitOfWorkFactory = Depends(get_uow_factory),
                     store: FileExportArtifactStore = Depends(get_artifact_store)) -> ExportOrder:
    return ExportOrder(factory, XlsxOrderExporter(), store)


def get_download_export(factory: UnitOfWorkFactory = Depends(get_uow_factory),
                        store: FileExportArtifactStore = Depends(get_artifact_store)) -> DownloadOrderExport:
    return DownloadOrderExport(factory, store)
