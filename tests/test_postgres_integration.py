"""Opt-in PostgreSQL checks; never fall back to the application's DATABASE_URL."""

import os
import unittest

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.domain.database import Database
from backend.infrastructure.config.settings import Settings


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL is not set")
class PostgresIntegrationTests(unittest.TestCase):
    def test_connection_and_session_recovery(self):
        settings = Settings(database_url=os.environ["TEST_DATABASE_URL"], _env_file=None)
        database = Database(settings.database_url)
        try:
            database.check_connection()
            with database.session() as session:
                self.assertEqual(session.scalar(text("SELECT 1")), 1)

            # A PostgreSQL transaction must be rolled back after a SQL error.
            with self.assertRaises(DBAPIError) as error:
                with database.session() as session:
                    session.execute(text("SELECT 1 / 0"))
            self.assertEqual(error.exception.orig.sqlstate, "22012")

            with database.session() as session:
                self.assertEqual(session.scalar(text("SELECT 1")), 1)
            self.assertEqual(database.engine.pool.checkedout(), 0)
        finally:
            database.dispose()


if __name__ == "__main__":
    unittest.main()
