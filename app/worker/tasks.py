from uuid import UUID

from taskiq import TaskiqEvents, TaskiqState

from app.ioc import create_container
from app.services.booking import BookingService
from app.worker.broker import broker

container = create_container()


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
