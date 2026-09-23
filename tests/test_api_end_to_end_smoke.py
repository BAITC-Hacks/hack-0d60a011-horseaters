"""One real HTTP/DB smoke path across import, calculation and procurement."""

import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.domain.entities.catalog import User
from backend.domain.enums import UserRole
from backend.infrastructure.api.dependencies import get_current_user
from backend.infrastructure.api.main import create_app
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database
from backend.infrastructure.persistence.models import Base
from backend.infrastructure.persistence.models.calculation import (
    CalculationRunImportModel,
    DemandForecastModel,
)
from backend.infrastructure.persistence.models.catalog import UserModel
from backend.infrastructure.persistence.models.orders import OrderExportModel, PurchaseOrderModel


def workbook(rows: list[dict]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


class ApiEndToEndSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.database = Database(f"sqlite:///{(root / 'smoke.db').as_posix()}")
        self.addCleanup(self.database.dispose)
        Base.metadata.create_all(self.database.engine)
        self.user_id = uuid4()
        self.auth_role = UserRole.BUYER
        with self.database.session() as session:
            session.add(UserModel(
                id=self.user_id, external_id="smoke-buyer", display_name="Smoke Buyer",
                role=UserRole.BUYER, is_active=True,
                created_at=datetime.now(timezone.utc),
            ))
        settings = Settings(
            database_url="postgresql+psycopg://test:unused@localhost:5432/smoke",
            order_export_directory=root / "exports", _env_file=None,
        )
        self.app = create_app(settings)
        self.app.dependency_overrides[get_current_user] = lambda: User(
            id=self.user_id, external_id="smoke-buyer", display_name="Smoke Buyer",
            role=self.auth_role,
        )

    @staticmethod
    def import_xlsx(client: TestClient, source: str, rows: list[dict]):
        return client.post(
            "/api/imports", data={"source_type": source},
            files={"file": (f"{source}.xlsx", workbook(rows),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    def test_import_to_approved_export(self):
        now = datetime.now(timezone.utc)
        sales = [
            {"Дата": (now - timedelta(days=days)).date().isoformat(),
             "Артикул": "SMOKE-1", "Номенклатура": "Cable", "Склад": "WH-SMOKE",
             "Количество": 5, "Цена": 10}
            for days in (28, 21, 14, 7)
        ]
        with patch("backend.infrastructure.api.main.Database", return_value=self.database), \
             TestClient(self.app) as client:
            sales_response = self.import_xlsx(client, "sales", sales)
            self.assertEqual(sales_response.status_code, 201, sales_response.text)
            terms_response = self.import_xlsx(client, "supplier_terms", [
                {"Артикул": "SMOKE-1", "Поставщик": "SUP-SMOKE", "MOQ": 5}
            ])
            self.assertEqual(terms_response.status_code, 201, terms_response.text)
            self.assertEqual(terms_response.json()["status"], "completed")

            run_response = client.post("/api/calculation-runs", json={
                "demand_source": "transactions", "horizon_days": 30,
            })
            self.assertEqual(run_response.status_code, 201, run_response.text)
            run = run_response.json()
            self.assertEqual(run["status"], "completed")
            self.assertEqual(len(run["import_batch_ids"]), 2)
            run_id = run["id"]
            self.assertEqual(client.get(f"/api/calculation-runs/{run_id}").status_code, 200)
            trends = client.get(f"/api/calculation-runs/{run_id}/demand-trends")
            self.assertEqual(trends.status_code, 200, trends.text)
            self.assertEqual(len(trends.json()), 12)
            self.assertTrue(any(float(point["raw_demand"]) > 0 for point in trends.json()))

            page_response = client.get(f"/api/calculation-runs/{run_id}/recommendations")
            self.assertEqual(page_response.status_code, 200, page_response.text)
            page = page_response.json()
            self.assertEqual(page["total"], 1)
            recommendation = page["items"][0]
            recommendation_id = recommendation["id"]
            self.assertGreater(float(recommendation["recommended_quantity"]), 0)
            explanation = client.get(f"/api/recommendations/{recommendation_id}/explain")
            self.assertEqual(explanation.status_code, 200, explanation.text)
            self.assertIn("formula", explanation.json())
            self.assertEqual(explanation.json()["evidence"]["growth_source"], "calculated")

            adjusted_quantity = str(float(recommendation["recommended_quantity"]) + 5)
            adjustment = client.patch(f"/api/recommendations/{recommendation_id}", json={
                "version": recommendation["version"], "new_quantity": adjusted_quantity,
                "reason": "Smoke-test procurement adjustment",
            })
            self.assertEqual(adjustment.status_code, 200, adjustment.text)
            self.assertEqual(adjustment.json()["status"], "adjusted")
            stale = client.patch(f"/api/recommendations/{recommendation_id}", json={
                "version": recommendation["version"], "new_quantity": adjusted_quantity,
                "reason": "Stale version must fail",
            })
            self.assertEqual(stale.status_code, 409, stale.text)

            accepted = client.post(f"/api/recommendations/{recommendation_id}/accept", json={
                "version": adjustment.json()["version"],
            })
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(accepted.json()["status"], "accepted")
            self.assertEqual(client.post(f"/api/recommendations/{recommendation_id}/accept", json={
                "version": adjustment.json()["version"],
            }).status_code, 409)

            orders_response = client.post("/api/orders", json={"calculation_run_id": run_id})
            self.assertEqual(orders_response.status_code, 201, orders_response.text)
            orders = orders_response.json()
            self.assertEqual(len(orders), 1)
            order_id = orders[0]["id"]
            self.assertEqual(orders[0]["status"], "draft")
            self.assertEqual(len(orders[0]["items"]), 1)
            self.assertEqual(float(orders[0]["items"][0]["approved_quantity"]),
                             float(adjusted_quantity))
            self.assertEqual(client.get(f"/api/orders/{order_id}").status_code, 200)
            self.assertEqual(client.post(f"/api/orders/{order_id}/export").status_code, 409)

            self.assertEqual(client.post(f"/api/orders/{order_id}/approve").status_code, 403)
            self.auth_role = UserRole.ADMIN
            approved = client.post(f"/api/orders/{order_id}/approve")
            self.assertEqual(approved.status_code, 200, approved.text)
            self.assertEqual(approved.json()["status"], "approved")
            self.assertEqual(client.post(f"/api/orders/{order_id}/export").status_code, 403)
            self.auth_role = UserRole.BUYER
            metadata = client.post(f"/api/orders/{order_id}/export")
            self.assertEqual(metadata.status_code, 201, metadata.text)
            download = client.get(f"/api/orders/{order_id}/export")
            self.assertEqual(download.status_code, 200, download.text)
            self.assertTrue(download.content.startswith(b"PK"))
            self.assertEqual(hashlib.sha256(download.content).hexdigest(),
                             metadata.json()["file_checksum"])
            self.assertIn("X-Request-ID", download.headers)

        with self.database.session() as session:
            self.assertEqual(session.scalar(select(func.count(CalculationRunImportModel.import_batch_id))), 2)
            self.assertEqual(session.scalar(select(func.count(DemandForecastModel.id))), 1)
            self.assertEqual(session.scalar(select(func.count(PurchaseOrderModel.id))), 1)
            self.assertEqual(session.scalar(select(func.count(OrderExportModel.id))), 1)


if __name__ == "__main__":
    unittest.main()
