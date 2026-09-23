from __future__ import annotations

from io import BytesIO
from typing import Sequence

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


class OpenpyxlOrderWorkbookExporter:
    """Render the fixed, flat XLSX contract consumed by 1C."""

    def render(self, rows: Sequence[OrderExportRow]) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Заказ"
        sheet.append(ORDER_EXPORT_COLUMNS)

        for cell in sheet[1]:
            cell.font = Font(bold=True)

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
            sheet.cell(sheet.max_row, 10).number_format = "dd.mm.yyyy"

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.column_dimensions["A"].width = 20
        sheet.column_dimensions["B"].width = 28
        sheet.column_dimensions["C"].width = 24
        sheet.column_dimensions["D"].width = 18
        sheet.column_dimensions["E"].width = 42
        for column in ("F", "G", "H", "I"):
            sheet.column_dimensions[column].width = 24
        sheet.column_dimensions["J"].width = 18

        output = BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()
