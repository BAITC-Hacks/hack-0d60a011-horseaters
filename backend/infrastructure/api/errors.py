from collections.abc import Callable
from typing import TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.application.ports.export_artifacts import ExportArtifactUnavailableError
from backend.application.use_cases.import_file import InvalidImportFileError
from backend.application.use_cases.export_order import OrderExportReferenceError
from backend.domain.errors import InvalidEntityStateError
from backend.domain.repositories.import_repository import DuplicateImportError, InvalidImportStatusTransitionError
from backend.domain.repositories.order_repository import (
    OrderNotFoundError, DuplicateOrderNumberError, RecommendationAlreadyOrderedError, InvalidOrderPersistenceStateError,
)
from backend.domain.repositories.recommendation_repository import RecommendationConflictError, RecommendationNotFoundError
from backend.infrastructure.excel.readers import ExcelImportValidationError, REQUIRED
from backend.infrastructure.persistence.import_gateway import ImportUserNotFoundError
from .schemas.errors import ErrorResponse, error_response

T = TypeVar("T")
ERROR_RESPONSES = {code: {"model": ErrorResponse} for code in (403, 404, 409, 422, 500, 503)}


def safe_issues(issues) -> list[dict]:
    known = {name for names in REQUIRED.values() for name in names}
    result = []
    for issue in (issues or [])[:50]:
        if not isinstance(issue, dict):
            continue
        if "missing_columns" in issue:
            result.append({"missing_columns": [name for name in issue["missing_columns"] if name in known]})
        elif type(issue.get("row")) is int:
            result.append({"row": issue["row"], "message": "invalid row values"})
        else:
            result.append({"message": "invalid workbook columns"})
    return result


def invoke(operation: Callable[..., T], *args, **kwargs) -> T:
    """Translate known use-case failures; unexpected exceptions remain server errors."""
    try:
        return operation(*args, **kwargs)
    except (RecommendationNotFoundError, OrderNotFoundError, ImportUserNotFoundError):
        raise HTTPException(404, detail={"code": "not_found"}) from None
    except (RecommendationConflictError, InvalidEntityStateError, InvalidOrderPersistenceStateError,
            DuplicateOrderNumberError, RecommendationAlreadyOrderedError, InvalidImportStatusTransitionError,
            OrderExportReferenceError):
        raise HTTPException(409, detail={"code": "state_conflict"}) from None
    except DuplicateImportError:
        raise HTTPException(409, detail={"code": "duplicate_import"}) from None
    except ExcelImportValidationError as error:
        issues = safe_issues(error.issues)
        raise HTTPException(422, detail={
            "code": "invalid_import_data", "status": "failed", "row_count": 0,
            "import_batch_id": str(error.batch_id) if hasattr(error, "batch_id") else None,
            "validation_errors": issues,
        }) from None
    except InvalidImportFileError:
        raise HTTPException(422, detail={"code": "invalid_import_file"}) from None
    except PermissionError:
        raise HTTPException(403, detail={"code": "forbidden"}) from None
    except LookupError as error:
        if type(error) is not LookupError:
            raise
        raise HTTPException(404, detail={"code": "not_found"}) from None
    except ValueError:
        raise HTTPException(422, detail={"code": "invalid_input"}) from None


def require_result(value: T | None) -> T:
    if value is None:
        raise HTTPException(404, detail={"code": "not_found"})
    return value


def install_error_handlers(app: FastAPI) -> None:
    async def unavailable(request: Request, error: Exception):
        return JSONResponse(status_code=503, content=error_response(
            code="service_unavailable", message="Service unavailable",
            request_id=request.state.request_id,
        ))

    async def internal_error(request: Request, error: Exception):
        return JSONResponse(status_code=500, content=error_response(
            code="internal_error", message="Internal server error",
            request_id=request.state.request_id,
        ))

    app.add_exception_handler(ExportArtifactUnavailableError, unavailable)
    app.add_exception_handler(SQLAlchemyError, unavailable)
    app.add_exception_handler(IntegrityError, internal_error)
