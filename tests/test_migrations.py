"""Offline PostgreSQL migration checks; no running database required."""

import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

from backend.infrastructure.persistence.models import Base


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "backend/infrastructure/persistence/migrations"


def offline_sql(*arguments):
    environment = dict(os.environ)
    # Includes percent escapes: the URL must never pass through INI interpolation.
    environment["DATABASE_URL"] = (
        "postgresql+psycopg://offline_user:offline%40secret%25@127.0.0.1:1/offline_db"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", *arguments, "--sql"],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=45,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout, result.stderr


class MigrationStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upgrade_sql, cls.upgrade_log = offline_sql("upgrade", "head")
        cls.downgrade_sql, cls.downgrade_log = offline_sql("downgrade", "head:base")

    def test_single_initial_revision_and_syntax(self):
        scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
        self.assertEqual(scripts.get_heads(), ["0002"])
        self.assertIsNone(scripts.get_revision("0001").down_revision)
        self.assertEqual(scripts.get_revision("0002").down_revision, "0001")
        self.assertEqual(len(list(scripts.walk_revisions())), 2)
        for path in MIGRATIONS.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_upgrade_and_downgrade_cover_exactly_the_model_tables(self):
        created = set(re.findall(r"CREATE TABLE (\w+)", self.upgrade_sql))
        dropped = set(re.findall(r"DROP TABLE (\w+)", self.downgrade_sql))
        expected = set(Base.metadata.tables) | {"alembic_version"}
        self.assertEqual(len(Base.metadata.tables), 25)
        self.assertEqual(created, expected)
        self.assertEqual(dropped, set(Base.metadata.tables))

    def test_every_constraint_and_index_is_rendered(self):
        dialect = postgresql.dialect()
        preparer = dialect.identifier_preparer
        for table in Base.metadata.tables.values():
            for constraint in table.constraints:
                name = preparer.format_constraint(constraint)
                self.assertIn("CONSTRAINT " + name, self.upgrade_sql)
                if isinstance(constraint, CheckConstraint):
                    self.assertIn("CONSTRAINT " + name + " CHECK", self.upgrade_sql)
                if isinstance(constraint, UniqueConstraint):
                    self.assertIn("CONSTRAINT " + name + " UNIQUE", self.upgrade_sql)
            for index in table.indexes:
                name = preparer.format_index(index)
                self.assertIn("INDEX " + name + " ON", self.upgrade_sql)
                self.assertIn("DROP INDEX " + name, self.downgrade_sql)
        self.assertIn("JSONB", self.upgrade_sql)
        self.assertIn("TIMESTAMP WITH TIME ZONE", self.upgrade_sql)
        self.assertNotIn("CREATE TYPE", self.upgrade_sql)

    def test_partial_indexes_and_descending_inventory_index(self):
        self.assertIn(
            "CREATE UNIQUE INDEX uq_import_batches_completed_checksum ON import_batches "
            "(file_checksum) WHERE status = 'completed'", self.upgrade_sql,
        )
        self.assertIn(
            "CREATE UNIQUE INDEX uq_supplier_products_primary_product ON supplier_products "
            "(product_id) WHERE is_active = true AND is_primary = true", self.upgrade_sql,
        )
        self.assertIn("(product_id, warehouse_id, snapshot_at DESC)", self.upgrade_sql)

    def test_offline_output_does_not_contain_credentials(self):
        output = self.upgrade_sql + self.upgrade_log + self.downgrade_sql + self.downgrade_log
        self.assertNotIn("offline_user", output)
        self.assertNotIn("offline%40secret", output)
        self.assertNotIn("offline@secret", output)

    def test_connection_error_does_not_expose_credentials(self):
        environment = dict(os.environ, DATABASE_URL=(
            "postgresql+psycopg://offline_user:offline%40secret%25@127.0.0.1:1/offline_db"
        ))
        script = """
import os
from unittest.mock import patch
import psycopg
from alembic import command
from alembic.config import Config
with patch('psycopg.connect', side_effect=psycopg.OperationalError(os.environ['DATABASE_URL'])):
    command.upgrade(Config('alembic.ini'), 'head')
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script], cwd=ROOT, env=environment,
            capture_output=True, text=True, timeout=45,
        )
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("PostgreSQL migration failed", output)
        self.assertNotIn("offline_user", output)
        self.assertNotIn("offline%40secret", output)
        self.assertNotIn("offline@secret", output)


if __name__ == "__main__":
    unittest.main()
