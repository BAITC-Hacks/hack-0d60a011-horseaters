from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.infrastructure.persistence.database import Database
from backend.infrastructure.persistence.application_uow import create_application_uow_factory
from backend.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory


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
