from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.domain.models import Booking, BookingStatus
from uuid6 import uuid7


class FakeBookingRepository:
    """In-memory репозиторий, имитирующий поведение БД."""

    def __init__(self) -> None:
        """Инициализирует пустое хранилище и счётчики."""
        self.items: dict[UUID, Booking] = {}
        self.commits = 0
        self.locked_reads: list[UUID] = []

    async def add(self, booking: Booking) -> None:
        """Сохраняет бронь, проставляя id и метки времени.

        Args:
            booking: Бронь для сохранения.
        """
        if booking.id is None:
            booking.id = uuid7()
        now = datetime.now(UTC)
        if booking.created_at is None:
            booking.created_at = now
        if booking.updated_at is None:
            booking.updated_at = now
        self.items[booking.id] = booking

    async def get(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь по id или None.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Бронь или None.
        """
        return self.items.get(booking_id)

    async def get_for_update(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь, фиксируя факт блокирующего чтения.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Бронь или None.
        """
        self.locked_reads.append(booking_id)
        return self.items.get(booking_id)

    async def list(
        self,
        *,
        status: BookingStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Booking], int]:
        """Возвращает страницу броней и общее количество по фильтру.

        Args:
            status: Фильтр по статусу или None.
            limit: Размер страницы.
            offset: Смещение.

        Returns:
            Кортеж из среза броней и общего количества.
        """
        matched = [b for b in self.items.values() if status is None or b.status is status]
        matched.sort(key=lambda b: b.created_at, reverse=True)
        return matched[offset : offset + limit], len(matched)

    async def delete(self, booking: Booking) -> None:
        """Удаляет бронь.

        Args:
            booking: Бронь для удаления.
        """
        self.items.pop(booking.id, None)

    async def commit(self) -> None:
        """Считает фиксацию транзакции."""
        self.commits += 1


class SpyConfirmationQueue:
    """Очередь-шпион: запоминает поставленные id, опционально падает."""

    def __init__(self, *, fail: bool = False) -> None:
        """Создаёт очередь.

        Args:
            fail: Бросать ли ошибку при постановке задачи.
        """
        self.enqueued: list[UUID] = []
        self._fail = fail

    async def enqueue(self, booking_id: UUID) -> None:
        """Запоминает id или бросает ошибку.

        Args:
            booking_id: Идентификатор брони.

        Raises:
            RuntimeError: Если очередь сконфигурирована на сбой.
        """
        if self._fail:
            raise RuntimeError("queue unavailable")
        self.enqueued.append(booking_id)


class StubConfirmationGateway:
    """Внешний сервис с заранее заданным результатом."""

    def __init__(self, *, result: bool) -> None:
        """Создаёт заглушку.

        Args:
            result: Что возвращать из confirm().
        """
        self._result = result

    def confirm(self) -> bool:
        """Возвращает заранее заданный результат.

        Returns:
            Фиксированный результат подтверждения.
        """
        return self._result
