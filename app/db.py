from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Создаёт async-движок SQLAlchemy.

    Args:
        settings: Настройки приложения со строкой подключения.

    Returns:
        Движок для работы с PostgreSQL.
    """
    return create_async_engine(
        url=settings.database_url,
        pool_size=10,
        pool_pre_ping=True,
        echo=False,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Создаёт фабрику async-сессий.

    Args:
        engine: Движок, к которому привязываются сессии.

    Returns:
        Фабрика сессий SQLAlchemy.
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False)
