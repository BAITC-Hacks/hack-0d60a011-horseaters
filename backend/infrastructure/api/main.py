from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.domain.database import Database
from backend.infrastructure.config.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings if settings is not None else Settings()
        database = Database(config.database_url)
        try:
            database.check_connection()
            app.state.database = database
            yield
        finally:
            database.dispose()

    return FastAPI(title="Warehouse replenishment", lifespan=lifespan)


app = create_app()
