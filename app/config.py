import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Конфигурация сервиса."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # Вероятность сбоя внешнего сервиса.
    FAILURE_RATE: float = Field(ge=0.0, le=1.0)

    # Rate limiting
    RATE_LIMIT_TIMES: int = Field(gt=0)
    RATE_LIMIT_SECONDS: int = Field(gt=0)

    # Логи.
    LOG_LEVEL: str

    @property
    def database_url(self) -> str:
        """Строка подключения к PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def redis_url(self) -> str:
        """Строка подключения к Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Возвращает настройки приложения.

    Returns:
        Единый объект настроек.
    """
    return Settings()
