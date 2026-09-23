from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.domain.database import Database


def get_db(request: Request) -> Iterator[Session]:
    """Provide one transaction per request through FastAPI Depends(get_db)."""
    database: Database = request.app.state.database
    with database.session() as session:
        yield session
