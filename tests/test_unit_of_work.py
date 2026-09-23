import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.infrastructure.persistence.unit_of_work import (
    RepositoryFactories,
    SqlAlchemyUnitOfWork,
)


class StubRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item_id: int) -> None:
        self.session.execute(
            text("INSERT INTO uow_items (id) VALUES (:item_id)"),
            {"item_id": item_id},
        )


class UnitOfWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE uow_items (id INTEGER PRIMARY KEY)"))
        self.sessions = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        factory = lambda session: StubRepository(session)
        self.factories = RepositoryFactories(
            imports=factory,
            sales=factory,
            inventory=factory,
            suppliers=factory,
            calculation_runs=factory,
            recommendations=factory,
            orders=factory,
        )

    def create_uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.sessions, self.factories)

    def count_items(self) -> int:
        with self.engine.connect() as connection:
            return connection.scalar(text("SELECT COUNT(*) FROM uow_items")) or 0

    def test_all_repositories_share_one_session(self):
        with self.create_uow() as uow:
            repositories = (
                uow.imports,
                uow.sales,
                uow.inventory,
                uow.suppliers,
                uow.calculation_runs,
                uow.recommendations,
                uow.orders,
            )
            sessions = {id(repository.session) for repository in repositories}
            self.assertEqual(len(sessions), 1)

    def test_explicit_commit_persists_changes(self):
        with self.create_uow() as uow:
            uow.sales.add(1)
            uow.commit()
        self.assertEqual(self.count_items(), 1)

    def test_exit_without_commit_rolls_back(self):
        with self.create_uow() as uow:
            uow.inventory.add(1)
        self.assertEqual(self.count_items(), 0)

    def test_exception_rolls_back_and_is_not_suppressed(self):
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with self.create_uow() as uow:
                uow.orders.add(1)
                raise RuntimeError("abort")
        self.assertEqual(self.count_items(), 0)

    def test_explicit_rollback_keeps_context_usable(self):
        with self.create_uow() as uow:
            uow.recommendations.add(1)
            uow.rollback()
            uow.recommendations.add(2)
            uow.commit()
        self.assertEqual(self.count_items(), 1)

    def test_repositories_and_transaction_methods_require_active_context(self):
        uow = self.create_uow()
        with self.assertRaisesRegex(RuntimeError, "inside a with block"):
            _ = uow.sales
        with self.assertRaisesRegex(RuntimeError, "inside a with block"):
            uow.commit()
        with self.assertRaisesRegex(RuntimeError, "inside a with block"):
            uow.rollback()

    def test_nested_context_is_rejected(self):
        uow = self.create_uow()
        with uow:
            with self.assertRaisesRegex(RuntimeError, "already active"):
                uow.__enter__()


if __name__ == "__main__":
    unittest.main()
