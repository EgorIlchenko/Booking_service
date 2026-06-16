from datetime import UTC, datetime, timedelta

from app.domain.models import Booking, BookingStatus, ServiceType


def future_dt(hours: int = 1) -> datetime:
    """Возвращает момент в будущем.

    Args:
        hours: Через сколько часов от текущего момента.

    Returns:
        Время встречи в будущем.
    """
    return datetime.now(UTC) + timedelta(hours=hours)


def build_booking(
    *,
    name: str = "Иван",
    status: BookingStatus = BookingStatus.PENDING,
    service_type: ServiceType = ServiceType.HAIRCUT,
    created_at: datetime | None = None,
) -> Booking:
    """Создаёт объект брони для тестов.

    Args:
        name: Имя клиента.
        status: Статус брони.
        service_type: Тип услуги.
        created_at: Явное время создания (для проверки сортировки).

    Returns:
        Не сохранённая бронь.
    """
    return Booking(
        name=name,
        datetime=future_dt(),
        service_type=service_type,
        status=status,
        created_at=created_at,
    )
