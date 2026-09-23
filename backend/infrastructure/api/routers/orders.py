from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from backend.application.dto.order import OrderExportCommand
from backend.application.ports.unit_of_work import UnitOfWorkFactory
from backend.application.use_cases.export_order import (
    ExportOrder,
    OrderExportReferenceError,
    OrderNotExportableError,
)
from backend.infrastructure.api.dependencies import get_uow_factory
from backend.infrastructure.api.exceptions import ApiError
from backend.infrastructure.excel.exporter import OpenpyxlOrderWorkbookExporter


router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/{order_id}/export")
def export_order(
    order_id: UUID,
    user_id: UUID = Query(..., description="User creating the audited export"),
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> Response:
    use_case = ExportOrder(uow_factory, OpenpyxlOrderWorkbookExporter())
    try:
        exported = use_case.execute(
            OrderExportCommand(order_id=order_id, user_id=user_id)
        )
    except LookupError as error:
        raise ApiError(404, "order_not_found", "Purchase order was not found") from error
    except OrderNotExportableError as error:
        raise ApiError(409, "order_not_exportable", str(error)) from error
    except OrderExportReferenceError as error:
        raise ApiError(409, "order_export_reference_missing", str(error)) from error

    return Response(
        content=exported.content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{exported.file_name}"',
            "X-Content-SHA256": exported.checksum,
        },
    )
