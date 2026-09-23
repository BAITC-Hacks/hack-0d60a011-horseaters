from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )


class DatabaseConnectionError(RuntimeError):
    """Safe connection error that never renders credentials."""


class Database:
    def __init__(self, url: str, *, echo: bool = False) -> None:
        self.engine = create_database_engine(url, echo=echo)
        self._sessions = create_session_factory(self.engine)

    def check_connection(self) -> None:
        """Execute a read-only readiness probe."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise DatabaseConnectionError(
                "Не удалось подключиться к PostgreSQL. Проверьте доступность "
                "сервера и DATABASE_URL: хост, порт, имя существующей базы, "
                "пользователя и пароль."
            ) from None

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Provide one transaction with commit or rollback on exit."""
        with self._sessions.begin() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()
