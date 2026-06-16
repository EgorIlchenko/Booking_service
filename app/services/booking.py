from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.models import Booking, BookingStatus
from app.domain.schemas import BookingCreate
from app.exceptions import BookingNotCancellable, BookingNotFound
from app.repositories.base import BookingRepository


class BookingConfirmationQueue(Protocol):
    """Исходящий порт постановки брони на фоновое подтверждение."""

    def enqueue(self, booking_id: UUID) -> None:
        """Ставит бронь в очередь на подтверждение.

        Args:
            booking_id: Идентификатор брони.
        """
        ...


class BookingService:
    """Сценарии работы с бронями поверх репозитория и очереди."""

    def __init__(self, repository: BookingRepository, queue: BookingConfirmationQueue) -> None:
        """Сохраняет зависимости сервиса.

        Args:
            repository: Хранилище броней.
            queue: Очередь фонового подтверждения.
        """
        self._repository = repository
        self._queue = queue

    async def create(self, data: BookingCreate) -> Booking:
        """Создаёт бронь в статусе pending и ставит её на подтверждение.

        Args:
            data: Данные новой брони.

        Returns:
            Сохранённая бронь.
        """
        booking = Booking(
            name=data.name,
            datetime=data.datetime,
            service_type=data.service_type,
            status=BookingStatus.PENDING,
        )
        await self._repository.add(booking=booking)
        await self._repository.commit()
        self._queue.enqueue(booking_id=booking.id)
        return booking

    async def get(self, booking_id: UUID) -> Booking:
        """Возвращает бронь по идентификатору.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Найденная бронь.

        Raises:
            BookingNotFound: Брони с таким идентификатором нет.
        """
        booking = await self._repository.get(booking_id=booking_id)
        if booking is None:
            raise BookingNotFound(booking_id=booking_id)
        return booking

    async def list(
        self,
        *,
        status: BookingStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Booking], int]:
        """Возвращает страницу броней и общее количество.

        Args:
            status: Фильтр по статусу или None для всех.
            limit: Размер страницы.
            offset: Смещение от начала выборки.

        Returns:
            Кортеж из списка броней страницы и общего количества по фильтру.
        """
        return await self._repository.list(status=status, limit=limit, offset=offset)

    async def cancel(self, booking_id: UUID) -> None:
        """Отменяет бронь, если она ещё в статусе pending.

        Args:
            booking_id: Идентификатор брони.

        Raises:
            BookingNotFound: Брони с таким идентификатором нет.
            BookingNotCancellable: Бронь уже не в статусе pending.
        """
        booking = await self._repository.get(booking_id=booking_id)
        if booking is None:
            raise BookingNotFound(booking_id=booking_id)
        if booking.status is not BookingStatus.PENDING:
            raise BookingNotCancellable(booking_id=booking_id)
        await self._repository.delete(booking=booking)
        await self._repository.commit()
