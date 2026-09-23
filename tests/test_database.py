import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import psycopg
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.infrastructure.api.dependencies import get_db
from backend.infrastructure.api.main import create_app
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database


POSTGRES_URL = "postgresql+psycopg://test_user:unused@localhost:5432/warehouse_test"


class DatabaseTests(unittest.TestCase):
    def test_connection_check_executes_only_select_one(self):
        database = Database("sqlite:///:memory:")
        statements = []

        @event.listens_for(database.engine, "before_cursor_execute")
        def capture_statement(connection, cursor, statement, parameters, context, many):
            statements.append(statement)

        try:
            database.check_connection()
            self.assertEqual(statements, ["SELECT 1"])
        finally:
            database.dispose()

    def test_postgres_engine_and_session_are_lazy(self):
        with patch("psycopg.connect", side_effect=AssertionError("Unexpected connection")):
            database = Database(POSTGRES_URL)
            try:
                self.assertEqual(database.engine.dialect.name, "postgresql")
                self.assertEqual(database.engine.dialect.driver, "psycopg")
                with database.session() as session:
                    self.assertIs(session.get_bind(), database.engine)
            finally:
                database.dispose()

    def test_commit_rollback_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{Path(directory).as_posix()}/test.db"
            database = Database(url)
            try:
                database.check_connection()
                with database.session() as session:
                    session.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY)"))
                with database.session() as session:
                    session.execute(text("INSERT INTO items VALUES (1)"))
                with self.assertRaises(IntegrityError):
                    with database.session() as session:
                        session.execute(text("INSERT INTO items VALUES (2)"))
                        session.execute(text("INSERT INTO items VALUES (1)"))
                self.assertEqual(database.engine.pool.checkedout(), 0)
            finally:
                database.dispose()

            reopened = Database(url)
            try:
                with reopened.session() as session:
                    self.assertEqual(
                        session.execute(text("SELECT id FROM items")).scalars().all(),
                        [1],
                    )
            finally:
                reopened.dispose()

    def test_fastapi_request_transactions(self):
        # Explicit, file-backed SQLite isolates transaction tests from any server.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database = Database(f"sqlite:///{Path(directory.name).as_posix()}/api.db")
        self.addCleanup(database.dispose)
        app = create_app(Settings(database_url=POSTGRES_URL, _env_file=None))

        @app.post("/items/{item_id}")
        def add_item(item_id: int, session: Session = Depends(get_db, scope="function")):
            session.execute(text("INSERT INTO items VALUES (:id)"), {"id": item_id})
            if item_id == 2:
                raise ValueError("Abort transaction")
            return {"id": item_id}

        with patch("backend.infrastructure.api.main.Database", return_value=database) as factory, \
                patch.object(database, "dispose", wraps=database.dispose) as dispose, \
                TestClient(app, raise_server_exceptions=False) as client:
            factory.assert_called_once_with(POSTGRES_URL, echo=False)
            with app.state.database.session() as session:
                session.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY)"))
            self.assertEqual(client.post("/items/1").status_code, 200)
            self.assertEqual(client.post("/items/2").status_code, 500)
            # A commit/SQL failure must be reported before sending a success response.
            self.assertEqual(client.post("/items/1").status_code, 500)
            with app.state.database.session() as session:
                self.assertEqual(session.scalar(text("SELECT COUNT(*) FROM items")), 1)
            self.assertEqual(database.engine.pool.checkedout(), 0)
        dispose.assert_called_once_with()

    def test_database_failure_keeps_liveness_and_reports_readiness(self):
        app = create_app(Settings(database_url=POSTGRES_URL, _env_file=None))
        database = Database(POSTGRES_URL)
        self.addCleanup(database.dispose)
        with (
            patch("backend.infrastructure.api.main.Database", return_value=database),
            patch.object(database, "dispose", wraps=database.dispose) as dispose,
            patch(
                "psycopg.connect",
                side_effect=psycopg.OperationalError(f"Connection failed: {POSTGRES_URL}"),
            ) as connect,
        ):
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                response = client.get("/health/db")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["detail"]["code"], "http_503")
                self.assertNotIn("unused", response.text)
            dispose.assert_called_once_with()
            connect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
