from fastapi import APIRouter, HTTPException, Request, status

from backend.infrastructure.persistence.database import (
    Database,
    DatabaseConnectionError,
)


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def database_health(request: Request) -> dict[str, str]:
    database: Database = request.app.state.database
    try:
        database.check_connection()
    except DatabaseConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from None
    return {"status": "ok", "database": "available"}
