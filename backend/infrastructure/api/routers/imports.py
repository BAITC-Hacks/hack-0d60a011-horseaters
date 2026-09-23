from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError

from backend.application.use_cases.import_data import ImportData, ImportDataCommand, ImportDataFile
from backend.application.use_cases.import_file import ImportFileUseCase, InvalidImportFileError
from backend.domain.enums import ImportSourceType
from backend.domain.repositories.import_repository import DuplicateImportError
from backend.infrastructure.api.schemas.imports import ImportResponse, ImportStatusResponse
from backend.infrastructure.excel.readers import ExcelImportReader, ExcelImportValidationError
from backend.infrastructure.persistence.import_gateway import (
    ImportUserNotFoundError,
    SqlAlchemyImportGateway,
)
from backend.infrastructure.persistence.import_repository import SqlAlchemyImportRepository
from backend.infrastructure.persistence.database import Database


router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.get("/{batch_id}", response_model=ImportStatusResponse)
def get_import_status(request: Request, batch_id: UUID) -> ImportStatusResponse:
    database: Database = request.app.state.database
    with database.session_factory() as session:
        batch = SqlAlchemyImportRepository(session).get(batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "import_not_found"},
        )
    return ImportStatusResponse(
        batch_id=batch.id,
        source_type=batch.source_type,
        status=batch.status,
        row_count=batch.row_count,
        file_checksum=batch.file_checksum,
        validation_errors=(batch.error_details or {}).get("validation_errors", []),
        file_name=batch.file_name,
        error_details=batch.error_details,
    )


@router.post("", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
def import_file(
    request: Request,
    source_type: Annotated[ImportSourceType, Form()],
    imported_by: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> ImportResponse:
    database: Database = request.app.state.database
    use_case = ImportData(ImportFileUseCase(
        ExcelImportReader(), SqlAlchemyImportGateway(database.session_factory),
    ))
    try:
        result = use_case.execute(
            ImportDataCommand(
                source_type=source_type,
                file=ImportDataFile(file.filename or "", file.file.read()),
                user_id=imported_by,
            )
        )
    except DuplicateImportError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_import", "checksum": error.file_checksum},
        ) from None
    except ImportUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "import_user_not_found"},
        ) from None
    except InvalidImportFileError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_import_file", "message": str(error)},
        ) from None
    except ExcelImportValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_import_data",
                "message": str(error),
                "issues": error.issues,
                "import_batch_id": str(error.batch_id) if hasattr(error, "batch_id") else None,
                "status": "failed",
                "row_count": 0,
                "validation_errors": error.issues,
            },
        ) from None
    except (ValueError, IntegrityError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "import_failed", "message": _safe_message(error)},
        ) from None
    return ImportResponse(
        batch_id=result.batch_id,
        source_type=result.source_type,
        status=result.status,
        row_count=result.row_count,
        file_checksum=result.file_checksum,
        validation_errors=list(result.validation_errors),
    )


def _safe_message(error: Exception) -> str:
    if isinstance(error, ValueError):
        return str(error)[:500]
    return "data violates database constraints"
