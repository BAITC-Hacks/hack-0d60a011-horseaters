import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.infrastructure.api.main import create_app
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database

POSTGRES_URL = "postgresql+psycopg://test_user:unused@localhost:5432/warehouse_test"


class ProcurementRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        sqlite_path = Path(self.directory.name, "health.db").as_posix()
        self.database = Database(f"sqlite:///{sqlite_path}")
        self.addCleanup(self.database.dispose)
        self.app = create_app(Settings(database_url=POSTGRES_URL, _env_file=None))

    def test_list_recommendations(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            res = client.get("/api/v1/procurement/recommendations")
            self.assertEqual(res.status_code, 200)
            items = res.json()
            self.assertIsInstance(items, list)
            self.assertGreaterEqual(len(items), 5)

            # Check F/UTP cable 200400085_
            cable = next((x for x in items if x["sku"] == "200400085_"), None)
            self.assertIsNotNone(cable)
            self.assertEqual(cable["package_multiplicity"], 305)
            self.assertEqual(cable["calculated_need"], 0)
            self.assertEqual(cable["urgency"], "NORMAL")

            # Check circuit breaker 010500004_
            breaker = next((x for x in items if x["sku"] == "010500004_"), None)
            self.assertIsNotNone(breaker)
            self.assertEqual(breaker["package_multiplicity"], 12)
            self.assertEqual(breaker["calculated_need"], 600)
            self.assertEqual(breaker["urgency"], "CRITICAL")

    def test_patch_recommendation_with_multiplicity_snapping(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            # Updating breaker (multiplicity 12) with raw quantity 43 -> should snap to 48
            res = client.patch(
                "/api/v1/procurement/recommendations/010500004_",
                json={"adjusted_need": 43, "snap_to_multiplicity": True, "adjustment_reason": "Проверка кратности"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["adjusted_need"], 48)
            self.assertEqual(data["total_cost"], 48 * data["unit_price"])
            self.assertIn("Ручная правка", data["reasoning"])

    def test_ai_sku_analysis_endpoint(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            # First fetch item
            res_item = client.get("/api/v1/procurement/recommendations/010500004_")
            self.assertEqual(res_item.status_code, 200)
            item = res_item.json()

            # Now call AI analysis
            res = client.post("/api/v1/ai/sku-analysis", json=item)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("summary", data)
            self.assertIn("root_cause", data)
            self.assertIn("risk_analysis", data)
            self.assertIn("recommendation_action", data)
            self.assertIn("confidence_score", data)
            self.assertIn("is_fallback", data)

    def test_ai_supplier_summary_endpoint(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            payload = {
                "supplier_name": "IEK Казахстан",
                "total_items": 10,
                "total_budget": 5200000,
                "critical_count": 3,
                "planned_count": 4,
                "normal_count": 3,
                "season_name": "Октябрь 2026",
                "season_factor": 1.242,
                "top_critical_items": [],
            }
            res = client.post("/api/v1/ai/supplier-summary", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("executive_summary", data)
            self.assertIn("budget_analysis", data)
            self.assertIn("critical_risks", data)
            self.assertIn("key_recommendations", data)

    def test_ai_supplier_letter_endpoint(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            payload = {
                "supplier_name": "IEK Казахстан",
                "company_name": "ТОО «Электрокомплект»",
                "items": [
                    {
                        "sku": "010500004_",
                        "item_name": "ВА47-29 6А",
                        "quantity": 600,
                        "unit": "шт",
                        "unit_price": 850,
                        "total_cost": 510000,
                    }
                ],
            }
            res = client.post("/api/v1/ai/supplier-letter", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("subject", data)
            self.assertIn("letter_body", data)
            self.assertIn("items_table", data)
            self.assertIn("closing", data)


if __name__ == "__main__":
    unittest.main()
