"""Check the configured PostgreSQL connection without changing the schema."""

from backend.domain.database import Database
from backend.infrastructure.config.settings import Settings


def main() -> None:
    database = Database(Settings().database_url)
    try:
        database.check_connection()
        print("PostgreSQL: соединение установлено (SELECT 1).")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
