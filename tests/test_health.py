import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.infrastructure.api.main import create_app
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database, DatabaseConnectionError


POSTGRES_URL = "postgresql+psycopg://test_user:unused@localhost:5432/warehouse_test"


class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        sqlite_path = Path(self.directory.name, "health.db").as_posix()
        self.database = Database(f"sqlite:///{sqlite_path}")
        self.addCleanup(self.database.dispose)
        self.app = create_app(Settings(database_url=POSTGRES_URL, _env_file=None))

    def test_liveness_and_database_readiness(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "ok"})
            self.assertEqual(
                client.get("/health/db").json(),
                {"status": "ok", "database": "available"},
            )

    def test_database_readiness_returns_503(self):
        with patch(
            "backend.infrastructure.api.main.Database",
            return_value=self.database,
        ), TestClient(self.app) as client, patch.object(
            self.database,
            "check_connection",
            side_effect=DatabaseConnectionError("safe failure"),
        ):
            response = client.get("/health/db")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {"detail": "database unavailable"})


if __name__ == "__main__":
    unittest.main()
