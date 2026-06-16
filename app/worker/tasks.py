from uuid import UUID

from taskiq import TaskiqEvents, TaskiqState

from app.config import get_settings
from app.ioc import create_container
from app.logging import configure_logging
from app.services.booking import BookingService
from app.worker.broker import broker

container = create_container()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def setup_worker(_state: TaskiqState) -> None:
    """Настраивает логирование при старте воркера.

    Args:
        _state: Состояние воркера TaskIQ (не используется).
    """
    configure_logging(level=get_settings().LOG_LEVEL)


@broker.task(task_name="process_booking", retry_on_error=True)
async def process_booking(booking_id: str) -> None:
    """Подтверждает бронь в фоне.

    Args:
        booking_id: Идентификатор брони в виде строки.
    """
    async with container() as request:
        service = await request.get(BookingService)
        await service.process(booking_id=UUID(booking_id))


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def close_container(_state: TaskiqState) -> None:
    """Закрывает DI-контейнер при остановке воркера.

    Args:
        _state: Состояние воркера TaskIQ (не используется).
    """
    await container.close()
