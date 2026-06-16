from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.v1.bookings import router as bookings_router
from app.api.v1.health import router as health_router
from app.ioc import create_container
from app.worker.broker import broker


def create_app() -> FastAPI:
    """Собирает и настраивает приложение FastAPI.

    Returns:
        Готовое приложение.
    """
    container = create_container()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Поднимает брокер на старте и закрывает ресурсы на остановке."""
        await broker.startup()
        yield
        await broker.shutdown()
        await container.close()

    app = FastAPI(title="Booking Service", version="1.0.0", lifespan=lifespan)
    setup_dishka(container, app)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(bookings_router, prefix="/api/v1")
    return app


app = create_app()
