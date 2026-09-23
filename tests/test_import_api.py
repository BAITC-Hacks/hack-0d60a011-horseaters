import tempfile
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.domain.enums import ImportStatus, UserRole
from backend.infrastructure.api.main import create_app
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database
from backend.infrastructure.persistence.models import Base
from backend.infrastructure.persistence.models.catalog import ProductModel, UserModel, WarehouseModel
from backend.infrastructure.persistence.models.imports import (
    ImportBatchModel,
    InventorySnapshotModel,
    SalesTransactionModel,
)


POSTGRES_URL = "postgresql+psycopg://test:unused@localhost:5432/import_test"


def workbook(rows: list[dict]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


class ImportApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name, "imports.db").as_posix()
        self.database = Database(f"sqlite:///{path}")
        self.addCleanup(self.database.dispose)
        Base.metadata.create_all(self.database.engine)
        self.user_id = uuid4()
        with self.database.session() as session:
            session.add(
                UserModel(
                    id=self.user_id,
                    external_id="buyer-import",
                    display_name="Import Buyer",
                    role=UserRole.BUYER,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )
        self.app = create_app(Settings(database_url=POSTGRES_URL, _env_file=None))

    def post(self, client: TestClient, source: str, content: bytes, name="source.xlsx"):
        return client.post(
            "/api/imports",
            data={"source_type": source, "imported_by": str(self.user_id)},
            files={
                "file": (
                    name,
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    def test_sales_import_is_persisted_and_duplicate_is_rejected(self):
        content = workbook(
            [
                {
                    "Дата": "2026-09-01",
                    "Артикул": "SKU-1",
                    "Номенклатура": "Cable",
                    "Склад": "WH-1",
                    "Количество": 5,
                    "Цена": 12,
                    "Обезличенный ID клиента": "anon-42",
                },
                {
                    "Дата": "2026-09-02",
                    "Артикул": "SKU-1",
                    "Номенклатура": "Cable",
                    "Склад": "WH-1",
                    "Количество": -1,
                    "Тип операции": "Возврат",
                },
            ]
        )
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            response = self.post(client, "sales", content, "sales.xlsx")
            duplicate = self.post(client, "sales", content, "sales-copy.xlsx")

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["row_count"], 2)
        self.assertEqual(duplicate.status_code, 409)
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            status_response = client.get(
                f"/api/imports/{response.json()['batch_id']}"
            )
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["file_name"], "sales.xlsx")
        with self.database.session() as session:
            self.assertEqual(session.scalar(select(func.count(SalesTransactionModel.id))), 2)
            self.assertEqual(session.scalar(select(func.count(ProductModel.id))), 1)
            self.assertEqual(session.scalar(select(func.count(WarehouseModel.id))), 1)

    def test_invalid_workbook_records_failed_batch(self):
        content = workbook([{"Артикул": "SKU-1"}])
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            response = self.post(client, "sales", content)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "invalid_import_data")
        self.assertEqual(response.json()["detail"]["status"], "failed")
        self.assertEqual(response.json()["detail"]["row_count"], 0)
        with self.database.session() as session:
            batch = session.scalar(select(ImportBatchModel))
            self.assertEqual(batch.status, ImportStatus.FAILED)
            self.assertIn("ExcelImportValidationError", batch.error_details["error_type"])
            self.assertEqual(response.json()["detail"]["import_batch_id"], str(batch.id))
            self.assertEqual(
                response.json()["detail"]["validation_errors"],
                batch.error_details["validation_errors"],
            )

    def test_fact_rows_are_atomic_when_database_constraint_fails(self):
        duplicate_rows = [
            {
                "Артикул": "SKU-1",
                "Склад": "WH-1",
                "Дата": "2026-09-01",
                "Остаток": 5,
            },
            {
                "Артикул": "SKU-1",
                "Склад": "WH-1",
                "Дата": "2026-09-01",
                "Остаток": 7,
            },
        ]
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            response = self.post(client, "inventory", workbook(duplicate_rows))

        self.assertEqual(response.status_code, 422, response.text)
        with self.database.session() as session:
            self.assertEqual(
                session.scalar(select(func.count(InventorySnapshotModel.id))), 0
            )
            batch = session.scalar(select(ImportBatchModel))
            self.assertEqual(batch.status, ImportStatus.FAILED)

    def test_unknown_import_user_returns_404_without_batch(self):
        self.user_id = uuid4()
        content = workbook(
            [{"Дата": "2026-09-01", "Артикул": "A", "Склад": "W", "Количество": 1}]
        )
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            response = self.post(client, "sales", content)

        self.assertEqual(response.status_code, 404)
        with self.database.session() as session:
            self.assertEqual(session.scalar(select(func.count(ImportBatchModel.id))), 0)

    def test_all_supported_source_types_reach_completed(self):
        cases = {
            "sales": {
                "Дата": "2026-09-03", "Артикул": "S-1", "Склад": "W-1", "Количество": 1,
            },
            "monthly_sales": {
                "Артикул": "M-1", "Месяц": "2026-08-01", "Количество": 2,
            },
            "inventory": {
                "Артикул": "I-1", "Склад": "W-1", "Дата": "2026-09-03", "Остаток": 3,
            },
            "stockout": {
                "Артикул": "O-1", "Склад": "W-1", "Дата начала": "2026-09-01",
            },
            "in_transit": {
                "Артикул": "T-1", "Склад": "W-1", "Поставщик": "SUP-1", "Количество": 4,
            },
            "seasonality": {
                "Артикул": "SE-1", "Месяц": 9, "Коэффициент": 1.1,
            },
            "supplier_terms": {
                "Артикул": "P-1", "Поставщик": "SUP-2", "MOQ": 5,
            },
            "growth": {
                "Артикул": "G-1", "Прирост": 0.1, "Действует с": "2026-01-01",
            },
            "material_requirements": {
                "Артикул": "R-1", "Склад": "W-1", "Потребность": 6,
                "Дата потребности": "2026-10-01",
            },
        }
        responses = []
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            for source, row in cases.items():
                response = self.post(
                    client, source, workbook([row]), name=f"{source}.xlsx"
                )
                responses.append(response)

        for response in responses:
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["status"], "completed")

    def test_missing_batch_status_returns_404(self):
        with patch(
            "backend.infrastructure.api.main.Database", return_value=self.database
        ), TestClient(self.app) as client:
            response = client.get(f"/api/imports/{uuid4()}")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
