from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.domain.models import BookingStatus, ServiceType
from app.domain.schemas import BookingCreate, BookingRead
from pydantic import ValidationError


async def test_accepts_future_aware_datetime() -> None:
    booking = BookingCreate(
        name="Иван",
        datetime=datetime.now(UTC) + timedelta(hours=1),
        service_type=ServiceType.HAIRCUT,
    )

    assert booking.service_type is ServiceType.HAIRCUT


async def test_rejects_past_datetime() -> None:
    with pytest.raises(ValidationError):
        BookingCreate(
            name="Иван",
            datetime=datetime.now(UTC) - timedelta(seconds=1),
            service_type=ServiceType.HAIRCUT,
        )


async def test_naive_future_datetime_treated_as_utc() -> None:
    naive = (datetime.now(UTC) + timedelta(hours=1)).replace(tzinfo=None)

    booking = BookingCreate(name="Иван", datetime=naive, service_type=ServiceType.HAIRCUT)

    assert booking.datetime == naive


async def test_naive_past_datetime_rejected() -> None:
    naive = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)

    with pytest.raises(ValidationError):
        BookingCreate(name="Иван", datetime=naive, service_type=ServiceType.HAIRCUT)


@pytest.mark.parametrize("name", ["", "x" * 256])
async def test_rejects_invalid_name_length(name: str) -> None:
    with pytest.raises(ValidationError):
        BookingCreate(
            name=name,
            datetime=datetime.now(UTC) + timedelta(hours=1),
            service_type=ServiceType.HAIRCUT,
        )


async def test_rejects_unknown_service_type() -> None:
    with pytest.raises(ValidationError):
        BookingCreate(
            name="Иван",
            datetime=datetime.now(UTC) + timedelta(hours=1),
            service_type="dentist",
        )


async def test_read_serializes_from_orm_attributes() -> None:
    now = datetime.now(UTC)
    orm_like = SimpleNamespace(
        id=uuid4(),
        name="Иван",
        datetime=now,
        service_type=ServiceType.MASSAGE,
        status=BookingStatus.PENDING,
        created_at=now,
        updated_at=now,
    )

    read = BookingRead.model_validate(orm_like)

    assert read.name == "Иван"
    assert read.service_type is ServiceType.MASSAGE
    assert read.status is BookingStatus.PENDING
