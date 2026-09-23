from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from backend.application.dto.order import OrderExportRow


ORDER_EXPORT_COLUMNS = (
    "Номер заказа",
    "Поставщик",
    "Склад",
    "Артикул",
    "Наименование",
    "Рекомендованное количество",
    "Утверждённое количество",
    "Цена",
    "Сумма",
    "Дата поставки",
)


class XlsxOrderExporter:
    """Render the fixed, flat XLSX contract consumed by 1C."""

    def render(self, rows: Sequence[OrderExportRow]) -> bytes:
        workbook = Workbook()
        try:
            sheet = workbook.active
            sheet.title = "Заказ"
            sheet.append(ORDER_EXPORT_COLUMNS)
            for cell in sheet[1]:
                cell.font = Font(bold=True)
                cell.data_type = "s"

            for row in rows:
                sheet.append(
                    (
                        row.order_number,
                        row.supplier_name,
                        row.warehouse_name,
                        row.sku,
                        row.product_name,
                        row.recommended_quantity,
                        row.approved_quantity,
                        row.unit_price,
                        row.total_amount,
                        row.delivery_date,
                    )
                )
                for cell in sheet[sheet.max_row][:5]:
                    # Catalog values such as '=...' stay literal text, never formulas.
                    cell.data_type = "s"
                sheet.cell(sheet.max_row, 10).number_format = "dd.mm.yyyy"

            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            widths = (20, 28, 24, 18, 42, 24, 24, 24, 24, 18)
            for index, width in enumerate(widths, start=1):
                sheet.column_dimensions[chr(64 + index)].width = width

            with BytesIO() as stream:
                workbook.save(stream)
                return stream.getvalue()
        finally:
            workbook.close()


OpenpyxlOrderWorkbookExporter = XlsxOrderExporter
