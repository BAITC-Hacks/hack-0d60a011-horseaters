"""Database connection and transaction scope shared by repositories."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for database models."""


class DatabaseConnectionError(RuntimeError):
    """Connection check failed; the message is safe to show in startup logs."""


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, pool_pre_ping=True)
        self._sessions = sessionmaker(
            bind=self.engine, expire_on_commit=False, autoflush=False
        )

    def check_connection(self) -> None:
        """Fail immediately when the configured database is unavailable."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            # Driver errors may contain credentials; suppress their traceback chain.
            raise DatabaseConnectionError(
                "Не удалось подключиться к PostgreSQL. Проверьте доступность "
                "сервера и DATABASE_URL: хост, порт, имя существующей базы, "
                "пользователя и пароль."
            ) from None

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Commit on success, roll back on error, and always close the session."""
        with self._sessions.begin() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()
