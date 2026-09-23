"""Database configuration from environment variables or the root .env file."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: str = Field(repr=False)

    @model_validator(mode="before")
    @classmethod
    def require_database_url(cls, values: dict[str, Any]) -> dict[str, Any]:
        url = values.get("database_url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(
                "DATABASE_URL не задан. Укажите подключение PostgreSQL в .env "
                "или переменной окружения: "
                "postgresql+psycopg://user:password@localhost:5432/hackalem"
            )
        return values

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()
        message = (
            "DATABASE_URL должен быть корректным URL PostgreSQL с драйвером "
            "psycopg: postgresql+psycopg://user:password@localhost:5432/hackalem"
        )
        try:
            url = make_url(value)
        except (ArgumentError, ValueError):
            raise ValueError(message) from None
        if url.drivername != "postgresql+psycopg":
            raise ValueError(message)
        return value
