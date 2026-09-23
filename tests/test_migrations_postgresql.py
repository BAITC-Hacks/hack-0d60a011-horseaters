"""Opt-in destructive cycle, strictly limited to an empty dedicated test database."""

import os
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.exc import IntegrityError

from backend.infrastructure.persistence.models import Base


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("MIGRATION_TEST_DATABASE_URL"), "MIGRATION_TEST_DATABASE_URL is not set")
class MigrationPostgresTests(unittest.TestCase):
    def run_alembic(self, url, *arguments):
        environment = dict(os.environ, DATABASE_URL=url)
        result = subprocess.run(
            [sys.executable, "-B", "-m", "alembic", *arguments],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_schema_matches(self, engine):
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            self.assertEqual(set(inspector.get_table_names()), set(Base.metadata.tables) | {"alembic_version"})
            context = MigrationContext.configure(
                connection, opts={"compare_type": True, "compare_server_default": True},
            )
            self.assertEqual(compare_metadata(context, Base.metadata), [])
            # Alembic does not compare arbitrary CHECK constraints: inspect them explicitly.
            preparer = connection.dialect.identifier_preparer
            for table in Base.metadata.tables.values():
                expected_checks = {
                    preparer.format_constraint(c).strip('"')
                    for c in table.constraints if isinstance(c, sa.CheckConstraint)
                }
                actual_checks = {c["name"] for c in inspector.get_check_constraints(table.name)}
                self.assertEqual(actual_checks, expected_checks, table.name)
                expected_indexes = {index.name for index in table.indexes}
                actual_indexes = {
                    index["name"] for index in inspector.get_indexes(table.name)
                    if not index.get("duplicates_constraint")
                }
                self.assertEqual(actual_indexes, expected_indexes, table.name)
            self.assertEqual(connection.scalar(sa.text("SELECT version_num FROM alembic_version")), "0002")

    def assert_partial_uniqueness(self, engine):
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                users = Base.metadata.tables["users"]
                batches = Base.metadata.tables["import_batches"]
                suppliers = Base.metadata.tables["suppliers"]
                products = Base.metadata.tables["products"]
                terms = Base.metadata.tables["supplier_products"]
                user_id, product_id = uuid4(), uuid4()
                supplier_ids = [uuid4() for _ in range(3)]
                connection.execute(users.insert().values(
                    id=user_id, external_id="db03", display_name="Migration test", role="buyer",
                ))
                batch_values = dict(
                    source_type="sales", file_name="synthetic.xlsx", file_checksum="a" * 64,
                    imported_by=user_id, imported_at=datetime.now(timezone.utc),
                )
                for status in ("completed", "pending", "failed"):
                    connection.execute(batches.insert().values(**batch_values, status=status))
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(batches.insert().values(**batch_values, status="completed"))
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(batches.update().where(batches.c.status == "pending").values(status="completed"))

                connection.execute(products.insert().values(id=product_id, sku="db03", name="Test", unit="pcs"))
                for index, supplier_id in enumerate(supplier_ids):
                    connection.execute(suppliers.insert().values(id=supplier_id, code=f"db03-{index}", name="Test"))
                term_values = dict(product_id=product_id, moq=1, lead_time_days=0)
                connection.execute(terms.insert().values(**term_values, supplier_id=supplier_ids[0], is_primary=True))
                connection.execute(terms.insert().values(**term_values, supplier_id=supplier_ids[1], is_primary=False))
                connection.execute(terms.insert().values(**term_values, supplier_id=supplier_ids[2], is_primary=True, is_active=False))
                for changes in ({"supplier_id": supplier_ids[1], "is_primary": True},
                                {"supplier_id": supplier_ids[2], "is_active": True}):
                    supplier_id = changes.pop("supplier_id")
                    with self.assertRaises(IntegrityError):
                        with connection.begin_nested():
                            connection.execute(terms.update().where(terms.c.supplier_id == supplier_id).values(**changes))
            finally:
                transaction.rollback()

    def test_upgrade_downgrade_upgrade(self):
        url_text = os.environ["MIGRATION_TEST_DATABASE_URL"]
        url = sa.make_url(url_text)
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertTrue((url.database or "").startswith("hackalem_migration_test_"),
                        "Use a dedicated database named hackalem_migration_test_<suffix>")
        engine = sa.create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 10})
        try:
            # No destructive action is attempted until the database is proven empty.
            with engine.connect() as connection:
                self.assertEqual(connection.scalar(sa.text("SELECT current_database()")), url.database)
                self.assertEqual(connection.scalar(sa.text("SELECT current_schema()")), "public")
                objects = connection.execute(sa.text(
                    "SELECT n.nspname, c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'"
                )).all()
                self.assertEqual(objects, [], "Refusing to run a downgrade test on a nonempty database")

            self.run_alembic(url_text, "upgrade", "head")
            self.assert_schema_matches(engine)
            self.assert_partial_uniqueness(engine)
            print("DB-03: upgrade head OK; 25 tables, constraints and indexes verified")
            self.run_alembic(url_text, "downgrade", "base")
            with engine.connect() as connection:
                self.assertEqual(sa.inspect(connection).get_table_names(), ["alembic_version"])
                self.assertEqual(connection.scalar(sa.text("SELECT count(*) FROM alembic_version")), 0)
                remaining = connection.execute(sa.text(
                    "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname NOT IN ('alembic_version', 'alembic_version_pkc')"
                )).all()
                self.assertEqual(remaining, [])
            print("DB-03: downgrade base OK; only empty Alembic bookkeeping remains")
            self.run_alembic(url_text, "upgrade", "head")
            self.assert_schema_matches(engine)
            self.run_alembic(url_text, "check")
            print("DB-03: second upgrade head and alembic check OK")
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
