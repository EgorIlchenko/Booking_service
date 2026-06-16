import enum
import uuid
from collections.abc import Iterable
from datetime import datetime as dt

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid6 import uuid7


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


class ServiceType(enum.StrEnum):
    """Тип услуги, на которую записывается клиент."""

    CONSULTATION = "consultation"
    HAIRCUT = "haircut"
    MASSAGE = "massage"


class BookingStatus(enum.StrEnum):
    """Статус обработки брони."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


def _enum_values(enum_type: type[enum.Enum]) -> list[str]:
    """Возвращает значения перечисления для хранения в БД.

    Args:
        enum_type: Класс перечисления.

    Returns:
        Список строковых значений членов перечисления.
    """
    members: Iterable[enum.Enum] = enum_type
    return [member.value for member in members]


class Booking(Base):
    """Бронь на встречу."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    datetime: Mapped[dt] = mapped_column(DateTime(timezone=True))
    service_type: Mapped[ServiceType] = mapped_column(
        Enum(ServiceType, name="service_type", values_callable=_enum_values)
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", values_callable=_enum_values),
        default=BookingStatus.PENDING,
    )
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
