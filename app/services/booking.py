from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

import structlog

from app.domain.models import Booking, BookingStatus
from app.domain.schemas import BookingCreate
from app.exceptions import BookingNotCancellable, BookingNotFound
from app.repositories.base import BookingRepository

logger = structlog.get_logger(__name__)


class BookingConfirmationQueue(Protocol):
    """Исходящий порт постановки брони на фоновое подтверждение."""

    async def enqueue(self, booking_id: UUID) -> None:
        """Ставит бронь в очередь на подтверждение.

        Args:
            booking_id: Идентификатор брони.
        """
        ...


class ConfirmationGateway(Protocol):
    """Исходящий порт обращения к внешнему сервису подтверждения."""

    def confirm(self) -> bool:
        """Пытается подтвердить бронь во внешнем сервисе.

        Returns:
            True при успехе, False при сбое.
        """
        ...


class BookingService:
    """Сценарии работы с бронями поверх репозитория, очереди и внешнего сервиса."""

    def __init__(
        self,
        repository: BookingRepository,
        queue: BookingConfirmationQueue,
        confirmation: ConfirmationGateway,
    ) -> None:
        """Сохраняет зависимости сервиса.

        Args:
            repository: Хранилище броней.
            queue: Очередь фонового подтверждения.
            confirmation: Внешний сервис подтверждения брони.
        """
        self._repository = repository
        self._queue = queue
        self._confirmation = confirmation

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
        await self._queue.enqueue(booking_id=booking.id)
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

    async def process(self, booking_id: UUID) -> None:
        """Подтверждает бронь в фоне.

        Args:
            booking_id: Идентификатор брони.
        """
        booking = await self._repository.get_for_update(booking_id=booking_id)
        if booking is None or booking.status is not BookingStatus.PENDING:
            return

        if self._confirmation.confirm():
            booking.status = BookingStatus.CONFIRMED
            logger.info("booking_confirmed", booking_id=str(booking.id), name=booking.name)
        else:
            booking.status = BookingStatus.FAILED
            logger.warning("booking_failed", booking_id=str(booking.id))
        await self._repository.commit()
