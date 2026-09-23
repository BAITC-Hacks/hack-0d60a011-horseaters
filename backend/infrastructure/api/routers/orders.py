from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.application.use_cases.export_order import (
    ExportOrder,
    OrderExportReferenceError,
    OrderNotExportableError,
)
from backend.infrastructure.api.dependencies import get_uow_factory
from backend.infrastructure.api.exceptions import ApiError
from backend.infrastructure.excel.exporter import XlsxOrderExporter
from backend.domain.repositories.order_repository import OrderNotFoundError


router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/{order_id}/export")
def export_order(
    order_id: UUID,
    user_id: UUID = Query(..., description="User creating the audited export"),
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> Response:
    use_case = ExportOrder(uow_factory, XlsxOrderExporter())
    try:
        exported = use_case.execute(order_id, user_id=user_id)
    except OrderNotFoundError as error:
        raise ApiError(404, "order_not_found", "Purchase order was not found") from error
    except OrderNotExportableError as error:
        raise ApiError(409, "order_not_exportable", str(error)) from error
    except OrderExportReferenceError as error:
        raise ApiError(409, "order_export_reference_missing", str(error)) from error

    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.metadata.file_name}"'
            ),
            "X-Content-SHA256": exported.metadata.file_checksum,
        },
    )
