import unittest
from io import BytesIO
from uuid import uuid4

import pandas as pd

from backend.application.dto.imports import ImportFileCommand
from backend.domain.enums import ImportSourceType
from backend.infrastructure.excel.readers import (
    ExcelImportReader,
    ExcelImportValidationError,
)


def workbook(rows: list[dict]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


class ExcelImportReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = ExcelImportReader()
        self.user_id = uuid4()

    def read(self, source: ImportSourceType, rows: list[dict]):
        return self.reader.read(
            ImportFileCommand(
                source_type=source,
                file_name="source.xlsx",
                content=workbook(rows),
                imported_by=self.user_id,
            )
        )

    def test_reads_and_normalizes_all_supported_sources(self):
        cases = {
            ImportSourceType.SALES: {
                "Дата": "2026-09-01", "Артикул": "A-1", "Склад": "WH-1",
                "Количество": -2, "Тип операции": "Возврат", "Цена": "10,50",
            },
            ImportSourceType.MONTHLY_SALES: {
                "Артикул": "A-1", "Месяц": "2026-08-01", "Количество": 20,
            },
            ImportSourceType.INVENTORY: {
                "Артикул": "A-1", "Склад": "WH-1", "Дата": "2026-09-01",
                "Остаток": 15, "Резерв": 3,
            },
            ImportSourceType.STOCKOUT: {
                "Артикул": "A-1", "Склад": "WH-1", "Дата начала": "2026-08-01",
            },
            ImportSourceType.IN_TRANSIT: {
                "Артикул": "A-1", "Склад": "WH-1", "Поставщик": "SUP-1",
                "Количество": 30, "Дата поступления": "2026-10-01",
            },
            ImportSourceType.SEASONALITY: {
                "Артикул": "A-1", "Месяц": 9, "Коэффициент": "1,25",
            },
            ImportSourceType.SUPPLIER_TERMS: {
                "Артикул": "A-1", "Поставщик": "SUP-1", "MOQ": 20,
                "Срок поставки": 7,
            },
            ImportSourceType.GROWTH: {
                "Артикул": "A-1", "Прирост": "0,08", "Действует с": "2026-01-01",
            },
            ImportSourceType.MATERIAL_REQUIREMENTS: {
                "Артикул": "A-1", "Склад": "WH-1", "Потребность": 4,
                "Дата потребности": "2026-10-15",
            },
        }
        for source, row in cases.items():
            with self.subTest(source=source.value):
                parsed = self.read(source, [row])
                self.assertEqual(parsed.source_type, source)
                self.assertEqual(len(parsed.rows), 1)
                self.assertEqual(parsed.rows[0]["source_row_number"], 2)

        sale = self.read(ImportSourceType.SALES, [cases[ImportSourceType.SALES]]).rows[0]
        self.assertEqual(sale["transaction_type"], "return")
        self.assertLess(sale["quantity"], 0)
        inventory = self.read(
            ImportSourceType.INVENTORY, [cases[ImportSourceType.INVENTORY]]
        ).rows[0]
        self.assertEqual(inventory["quantity_available"], 12)

    def test_reports_missing_columns_and_row_numbers(self):
        with self.assertRaises(ExcelImportValidationError) as missing:
            self.read(ImportSourceType.SALES, [{"Артикул": "A-1"}])
        self.assertIn("warehouse_code", missing.exception.issues[0]["missing_columns"])

        with self.assertRaises(ExcelImportValidationError) as invalid:
            self.read(
                ImportSourceType.SALES,
                [{"Дата": "bad", "Артикул": "A-1", "Склад": "WH", "Количество": 1}],
            )
        self.assertEqual(invalid.exception.issues[0]["row"], 2)

    def test_converts_wide_monthly_inventory_and_seasonality_reports(self):
        monthly = self.read(
            ImportSourceType.MONTHLY_SALES,
            [{"Артикул": "A-1", "Январь 2026": 10, "Февраль 2026": 12}],
        )
        self.assertEqual(len(monthly.rows), 2)
        self.assertEqual(monthly.rows[0]["period_start"].month, 1)
        self.assertEqual(monthly.rows[1]["quantity"], 12)

        inventory = self.read(
            ImportSourceType.INVENTORY,
            [{"Артикул": "A-1", "Склад": "WH", "31.01.2026": 5, "28.02.2026": 7}],
        )
        self.assertEqual(len(inventory.rows), 2)
        self.assertEqual(inventory.rows[1]["snapshot_at"].day, 28)

        seasonality = self.read(
            ImportSourceType.SEASONALITY,
            [{"Артикул": "A-1", "Январь": 0.8, "Февраль": 1.2}],
        )
        self.assertEqual([row["month"] for row in seasonality.rows], [1, 2])

    def test_rejects_direct_customer_identifiers(self):
        with self.assertRaisesRegex(ExcelImportValidationError, "identifiers"):
            self.read(
                ImportSourceType.SALES,
                [{
                    "Дата": "2026-09-01", "Артикул": "A-1", "Склад": "WH",
                    "Количество": 1, "Телефон": "+7-000-000",
                }],
            )

    def test_customer_id_requires_explicit_anonymized_header_and_opaque_value(self):
        row = {"Дата": "2026-09-01", "Артикул": "A-1", "Склад": "WH", "Количество": 1}
        for header in ("ID клиента", "Клиент ID"):
            with self.subTest(header=header), self.assertRaises(ExcelImportValidationError):
                self.read(ImportSourceType.SALES, [{**row, header: "12345"}])
        for value in ("buyer@example.com", "+77001234567", "77001234567", "Иван Иванов"):
            with self.subTest(value=value), self.assertRaises(ExcelImportValidationError) as error:
                self.read(ImportSourceType.SALES, [{**row, "Обезличенный ID клиента": value}])
            self.assertNotIn(value, str(error.exception.issues))
        parsed = self.read(ImportSourceType.SALES, [{**row, "Обезличенный ID клиента": "anon-42"}])
        self.assertEqual(parsed.rows[0]["anonymous_customer_id"], "anon-42")


if __name__ == "__main__":
    unittest.main()
