from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.infrastructure.config.settings import Settings
from backend.infrastructure.api.routers.health import router as health_router
from backend.infrastructure.api.routers.imports import router as imports_router
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

    app = FastAPI(title="Warehouse replenishment", lifespan=lifespan)

    # Configure CORS for frontend access
    cors_origins_env = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    cors_origins = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
    if not cors_origins:
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(imports_router)

    # Versioned liveness endpoint used by Docker and orchestration.
    @app.get("/api/v1/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "service": "procurement-backend"}

    return app


app = create_app()
