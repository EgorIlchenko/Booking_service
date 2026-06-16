from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.models import Booking, BookingStatus


class BookingRepository(Protocol):
    """Контракт хранилища броней."""

    async def add(self, booking: Booking) -> None:
        """Добавляет новую бронь в текущую транзакцию.

        Args:
            booking: Бронь для сохранения.
        """
        ...

    async def get(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь по идентификатору.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Бронь или None, если её нет.
        """
        ...

    async def get_for_update(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь, блокируя строку.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Заблокированная бронь или None, если её нет.
        """
        ...

    async def list(
        self,
        *,
        status: BookingStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Booking], int]:
        """Возвращает страницу броней и их общее количество.

        Args:
            status: Фильтр по статусу или None для всех.
            limit: Размер страницы.
            offset: Смещение от начала выборки.

        Returns:
            Кортеж из списка броней страницы и общего количества по фильтру.
        """
        ...

    async def delete(self, booking: Booking) -> None:
        """Удаляет бронь.

        Args:
            booking: Бронь для удаления.
        """
        ...

    async def commit(self) -> None:
        """Фиксирует изменения текущей транзакции."""
        ...
