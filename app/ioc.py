from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db import create_engine, create_session_factory
from app.rate_limit import RedisRateLimiter
from app.repositories.base import BookingRepository
from app.repositories.sqlalchemy import SQLAlchemyBookingRepository
from app.services.booking import (
    BookingConfirmationQueue,
    BookingService,
    ConfirmationGateway,
)
from app.worker.confirmation import RandomConfirmationGateway
from app.worker.queue import TaskiqConfirmationQueue


class AppProvider(Provider):
    """Провайдеры зависимостей приложения."""

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        """Возвращает настройки приложения.

        Returns:
            Настройки приложения.
        """
        return get_settings()

    @provide(scope=Scope.APP)
    async def engine(self, settings: Settings) -> AsyncIterator[AsyncEngine]:
        """Создаёт движок БД и закрывает его при остановке.

        Args:
            settings: Настройки приложения.

        Yields:
            Async-движок SQLAlchemy.
        """
        engine = create_engine(settings)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        """Создаёт фабрику сессий.

        Args:
            engine: Движок БД.

        Returns:
            Фабрика async-сессий.
        """
        return create_session_factory(engine)

    @provide(scope=Scope.APP)
    def confirmation(self, settings: Settings) -> ConfirmationGateway:
        """Создаёт внешний сервис подтверждения брони.

        Args:
            settings: Настройки приложения с вероятностью сбоя.

        Returns:
            Реализация порта подтверждения.
        """
        return RandomConfirmationGateway(failure_rate=settings.FAILURE_RATE)

    @provide(scope=Scope.APP)
    async def redis(self, settings: Settings) -> AsyncIterator[Redis]:
        """Создаёт клиент Redis и закрывает его при остановке.

        Args:
            settings: Настройки приложения с адресом Redis.

        Yields:
            Async-клиент Redis.
        """
        client: Redis = Redis.from_url(url=settings.redis_url)
        yield client
        await client.aclose()

    @provide(scope=Scope.APP)
    def rate_limiter(self, settings: Settings, redis: Redis) -> RedisRateLimiter:
        """Создаёт лимитер запросов на Redis.

        Args:
            settings: Настройки приложения с параметрами лимита.
            redis: Клиент Redis.

        Returns:
            Лимитер запросов.
        """
        return RedisRateLimiter(
            redis=redis,
            times=settings.RATE_LIMIT_TIMES,
            seconds=settings.RATE_LIMIT_SECONDS,
        )

    @provide(scope=Scope.REQUEST)
    async def session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[AsyncSession]:
        """Открывает сессию на время запроса или задачи.

        Args:
            session_factory: Фабрика сессий.

        Yields:
            Открытая async-сессия.
        """
        async with session_factory() as session:
            yield session

    repository = provide(
        SQLAlchemyBookingRepository, scope=Scope.REQUEST, provides=BookingRepository
    )
    queue = provide(TaskiqConfirmationQueue, scope=Scope.APP, provides=BookingConfirmationQueue)
    service = provide(BookingService, scope=Scope.REQUEST)


def create_container() -> AsyncContainer:
    """Создаёт DI-контейнер приложения.

    Returns:
        Асинхронный контейнер Dishka.
    """
    return make_async_container(AppProvider())
