from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Booking, BookingStatus


class SQLAlchemyBookingRepository:
    """Репозиторий броней поверх async-сессии SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию, в которой выполняются операции.

        Args:
            session: Активная async-сессия.
        """
        self._session = session

    async def add(self, booking: Booking) -> None:
        """Добавляет новую бронь в текущую транзакцию.

        Args:
            booking: Бронь для сохранения.
        """
        self._session.add(booking)
        await self._session.flush()

    async def get(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь по идентификатору.

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Бронь или None, если её нет.
        """
        return await self._session.get(Booking, booking_id)

    async def get_for_update(self, booking_id: UUID) -> Booking | None:
        """Возвращает бронь, блокируя строку (SELECT ... FOR UPDATE).

        Args:
            booking_id: Идентификатор брони.

        Returns:
            Заблокированная бронь или None, если её нет.
        """
        return await self._session.get(Booking, booking_id, with_for_update=True)

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
        conditions = [Booking.status == status] if status is not None else []
        items_stmt = (
            select(Booking)
            .where(*conditions)
            .order_by(Booking.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(Booking).where(*conditions)

        items = (await self._session.execute(items_stmt)).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return items, int(total)

    async def delete(self, booking: Booking) -> None:
        """Удаляет бронь.

        Args:
            booking: Бронь для удаления.
        """
        await self._session.delete(booking)
        await self._session.flush()

    async def commit(self) -> None:
        """Фиксирует изменения текущей транзакции."""
        await self._session.commit()
