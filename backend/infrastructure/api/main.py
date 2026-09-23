from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.infrastructure.config.settings import Settings
from backend.infrastructure.api.routers.health import router as health_router
from backend.infrastructure.persistence.database import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings if settings is not None else Settings()
        database = Database(config.database_url, echo=config.db_echo)
        try:
            database.check_connection()
            app.state.database = database
            yield
        finally:
            database.dispose()

    application = FastAPI(title="Warehouse replenishment", lifespan=lifespan)
    application.include_router(health_router)
    return application


app = create_app()
