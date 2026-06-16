from datetime import UTC
from datetime import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import BookingStatus, ServiceType


class BookingCreate(BaseModel):
    """Данные для создания брони."""

    name: str = Field(min_length=1, max_length=255)
    datetime: dt
    service_type: ServiceType

    @field_validator("datetime")
    @classmethod
    def _must_be_future(cls, value: dt) -> dt:
        """Проверяет, что время встречи в будущем.

        Args:
            value: Время встречи из запроса.

        Returns:
            То же время, если проверка пройдена.
        """
        moment = value if value.tzinfo else value.replace(tzinfo=UTC)
        if moment <= dt.now(UTC):
            raise ValueError("Время встречи должно быть в будущем")
        return value


class BookingRead(BaseModel):
    """Представление брони в ответах."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    datetime: dt
    service_type: ServiceType
    status: BookingStatus
    created_at: dt
    updated_at: dt


class BookingList(BaseModel):
    """Страница списка броней."""

    items: list[BookingRead]
    total: int
    limit: int
    offset: int
