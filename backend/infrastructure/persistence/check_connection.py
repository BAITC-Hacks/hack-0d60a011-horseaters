"""Check the configured PostgreSQL connection without changing the schema."""

from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database


def main() -> None:
    settings = Settings()
    database = Database(settings.database_url, echo=settings.db_echo)
    try:
        database.check_connection()
        print("PostgreSQL: соединение установлено (SELECT 1).")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
