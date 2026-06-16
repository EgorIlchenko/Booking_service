from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

import pytest
from app.domain.models import Base, BookingStatus
from app.ioc import AppProvider
from app.main import create_app
from app.rate_limit import RedisRateLimiter
from app.repositories.base import BookingRepository
from app.services.booking import BookingConfirmationQueue, ConfirmationGateway
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from fakeredis import aioredis
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from tests.factories import build_booking
from tests.fakes import SpyConfirmationQueue, StubConfirmationGateway


class _TestProvider(Provider):
    """Подменяет внешние зависимости на тестовые двойники."""

    def __init__(self, *, queue: BookingConfirmationQueue, rate_times: int) -> None:
        """Сохраняет очередь-шпион и лимит запросов.

        Args:
            queue: Очередь, которую увидит сервис.
            rate_times: Разрешённое число запросов за окно.
        """
        super().__init__()
        self._queue = queue
        self._rate_times = rate_times

    @provide(scope=Scope.APP, override=True)
    async def engine(self) -> AsyncIterator[AsyncEngine]:
        """Создаёт in-memory SQLite-движок с поднятой схемой.

        Yields:
            Async-движок.
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

    @provide(scope=Scope.APP, override=True)
    async def redis(self) -> AsyncIterator[Redis]:
        """Создаёт поддельный Redis.

        Yields:
            Клиент fakeredis.
        """
        client: Redis = aioredis.FakeRedis()
        yield client
        await client.aclose()

    @provide(scope=Scope.APP, override=True)
    def queue(self) -> BookingConfirmationQueue:
        """Возвращает очередь-шпион.

        Returns:
            Очередь, заданная в конструкторе.
        """
        return self._queue

    @provide(scope=Scope.APP, override=True)
    def confirmation(self) -> ConfirmationGateway:
        """Возвращает заглушку внешнего сервиса (в API не используется).

        Returns:
            Заглушка подтверждения.
        """
        return StubConfirmationGateway(result=True)

    @provide(scope=Scope.APP, override=True)
    def rate_limiter(self, redis: Redis) -> RedisRateLimiter:
        """Создаёт лимитер с тестовым окном.

        Args:
            redis: Поддельный Redis.

        Returns:
            Лимитер запросов.
        """
        return RedisRateLimiter(redis=redis, times=self._rate_times, seconds=60)


@dataclass
class ApiContext:
    """Контекст e2e-теста: клиент, контейнер и очередь-шпион."""

    client: AsyncClient
    container: AsyncContainer
    queue: SpyConfirmationQueue


@asynccontextmanager
async def make_api_context(
    *,
    queue: SpyConfirmationQueue | None = None,
    rate_times: int = 1000,
) -> AsyncIterator[ApiContext]:
    """Поднимает приложение на тестовом контейнере.

    Args:
        queue: Очередь-шпион или None для новой.
        rate_times: Лимит запросов за окно.

    Yields:
        Контекст с готовым HTTP-клиентом.
    """
    queue = queue or SpyConfirmationQueue()
    container = make_async_container(
        AppProvider(),
        _TestProvider(queue=queue, rate_times=rate_times),
    )
    app = create_app(container=container)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield ApiContext(client=client, container=container, queue=queue)
        finally:
            await container.close()


@pytest.fixture
async def api() -> AsyncIterator[ApiContext]:
    """Контекст e2e-теста.

    Yields:
        Контекст приложения.
    """
    async with make_api_context() as context:
        yield context


async def seed_booking(container: AsyncContainer, *, status: BookingStatus) -> UUID:
    """Вставляет бронь нужного статуса напрямую через репозиторий.

    Args:
        container: DI-контейнер приложения.
        status: Статус создаваемой брони.

    Returns:
        Идентификатор созданной брони.
    """
    async with container() as request:
        repository = await request.get(BookingRepository)
        booking = build_booking(status=status)
        await repository.add(booking=booking)
        await repository.commit()
        return booking.id
