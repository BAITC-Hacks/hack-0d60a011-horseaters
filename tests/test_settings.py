import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from backend.infrastructure.config.settings import Settings


POSTGRES_URL = "postgresql+psycopg://test_user:unused@localhost:5432/warehouse_test"


class SettingsTests(unittest.TestCase):
    def test_missing_url_has_configuration_message(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValidationError, "DATABASE_URL не задан"):
                Settings(_env_file=None)

    def test_empty_url_has_configuration_message(self):
        for value in ("", "  "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValidationError, "DATABASE_URL не задан"):
                    Settings(database_url=value, _env_file=None)

    def test_rejects_other_drivers_and_invalid_urls(self):
        for value in (
            "sqlite:///warehouse.db",
            "postgresql://user:secret@localhost/warehouse",
            "postgresql+psycopg2://user:secret@localhost/warehouse",
            "postgresql+psycopg://user:secret@localhost:invalid/warehouse",
            "invalid-secret",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as error:
                    Settings(database_url=value, _env_file=None)
                self.assertIn("DATABASE_URL", str(error.exception))
                self.assertIn("psycopg", str(error.exception))
                self.assertNotIn("secret", str(error.exception))

    def test_reads_dotenv_and_environment_takes_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(f"DATABASE_URL={POSTGRES_URL}\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(Settings(_env_file=dotenv).database_url, POSTGRES_URL)
                override = POSTGRES_URL.replace("warehouse_test", "another_test")
                os.environ["DATABASE_URL"] = override
                self.assertEqual(Settings(_env_file=dotenv).database_url, override)

    def test_settings_repr_hides_credentials(self):
        settings = Settings(database_url=POSTGRES_URL, _env_file=None)
        self.assertNotIn("unused", repr(settings))


if __name__ == "__main__":
    unittest.main()
