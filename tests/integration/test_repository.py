from datetime import UTC, datetime, timedelta

from app.domain.models import Booking, BookingStatus, ServiceType
from app.repositories.sqlalchemy import SQLAlchemyBookingRepository
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import build_booking, future_dt


async def test_add_assigns_uuid7_and_timestamps(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    booking = Booking(
        name="Иван",
        datetime=future_dt(),
        service_type=ServiceType.HAIRCUT,
        status=BookingStatus.PENDING,
    )

    await repository.add(booking=booking)
    await repository.commit()

    assert booking.id is not None
    assert booking.id.version == 7
    assert booking.created_at is not None
    assert booking.updated_at is not None


async def test_status_defaults_to_pending_in_db(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    booking = Booking(name="Иван", datetime=future_dt(), service_type=ServiceType.HAIRCUT)

    await repository.add(booking=booking)
    await repository.commit()
    await session.refresh(booking)

    assert booking.status is BookingStatus.PENDING


async def test_get_returns_none_for_missing(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    booking = build_booking()
    await repository.add(booking)
    await repository.commit()

    assert await repository.get(booking.id) is not None
    await repository.delete(booking=booking)
    await repository.commit()
    assert await repository.get(booking.id) is None


async def test_get_for_update_returns_row(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    booking = build_booking()
    await repository.add(booking=booking)
    await repository.commit()

    locked = await repository.get_for_update(booking_id=booking.id)

    assert locked is not None
    assert locked.id == booking.id


async def test_list_filters_paginates_and_orders(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    base = datetime.now(UTC)
    for index in range(3):
        await repository.add(
            Booking(
                name=f"P{index}",
                datetime=future_dt(),
                service_type=ServiceType.HAIRCUT,
                status=BookingStatus.PENDING,
                created_at=base - timedelta(minutes=index),
            )
        )
    await repository.add(
        Booking(
            name="C",
            datetime=future_dt(),
            service_type=ServiceType.MASSAGE,
            status=BookingStatus.CONFIRMED,
            created_at=base,
        )
    )
    await repository.commit()

    items, total = await repository.list(status=BookingStatus.PENDING, limit=10, offset=0)
    assert total == 3
    assert [booking.name for booking in items] == ["P0", "P1", "P2"]

    _, total_all = await repository.list(status=None, limit=10, offset=0)
    assert total_all == 4

    page, total = await repository.list(status=BookingStatus.PENDING, limit=2, offset=1)
    assert total == 3
    assert [booking.name for booking in page] == ["P1", "P2"]


async def test_enum_stored_as_lowercase_value(session: AsyncSession) -> None:
    repository = SQLAlchemyBookingRepository(session=session)
    await repository.add(
        Booking(
            name="Иван",
            datetime=future_dt(),
            service_type=ServiceType.MASSAGE,
            status=BookingStatus.PENDING,
        )
    )
    await repository.commit()

    row = (await session.execute(text("SELECT service_type, status FROM bookings"))).one()

    assert row.service_type == "massage"
    assert row.status == "pending"
