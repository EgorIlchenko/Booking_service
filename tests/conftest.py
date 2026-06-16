from collections.abc import AsyncIterator

import pytest
from app.domain.models import Base
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Создаёт in-memory SQLite-движок с поднятой схемой.

    Yields:
        Async-движок с созданными таблицами.
    """
    engine = create_async_engine(
        url="sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Открывает сессию поверх тестового движка.

    Args:
        engine: Тестовый движок.

    Yields:
        Async-сессия.
    """
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
