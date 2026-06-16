from uuid import uuid4

import pytest
from app.domain.models import BookingStatus, ServiceType
from app.domain.schemas import BookingCreate
from app.exceptions import BookingNotCancellable, BookingNotFound
from app.services.booking import BookingService

from tests.factories import build_booking, future_dt
from tests.fakes import FakeBookingRepository, SpyConfirmationQueue, StubConfirmationGateway


def make_service(
    *,
    repository: FakeBookingRepository | None = None,
    queue: SpyConfirmationQueue | None = None,
    confirm: bool = True,
) -> tuple[BookingService, FakeBookingRepository, SpyConfirmationQueue]:
    """Собирает сервис на фейках и возвращает его вместе с ними.

    Args:
        repository: Репозиторий-фейк или None для нового.
        queue: Очередь-шпион или None для новой.
        confirm: Результат внешнего сервиса подтверждения.

    Returns:
        Сервис и его зависимости-двойники.
    """
    repository = repository or FakeBookingRepository()
    queue = queue or SpyConfirmationQueue()
    service = BookingService(repository, queue, StubConfirmationGateway(result=confirm))
    return service, repository, queue


async def test_create_persists_pending_and_enqueues() -> None:
    service, repository, queue = make_service()

    booking = await service.create(
        BookingCreate(name="Иван", datetime=future_dt(), service_type=ServiceType.HAIRCUT)
    )

    assert booking.status is BookingStatus.PENDING
    assert booking.id is not None
    assert repository.items[booking.id] is booking
    assert repository.commits == 1
    assert queue.enqueued == [booking.id]


async def test_create_commits_before_enqueue_so_failure_keeps_booking() -> None:
    repository = FakeBookingRepository()
    queue = SpyConfirmationQueue(fail=True)
    service, _, _ = make_service(repository=repository, queue=queue)

    with pytest.raises(RuntimeError):
        await service.create(
            BookingCreate(name="Иван", datetime=future_dt(), service_type=ServiceType.MASSAGE)
        )

    assert repository.commits == 1
    assert len(repository.items) == 1


async def test_get_returns_existing() -> None:
    service, repository, _ = make_service()
    booking = build_booking()
    await repository.add(booking)

    assert await service.get(booking.id) is booking


async def test_get_missing_raises_not_found() -> None:
    service, _, _ = make_service()

    with pytest.raises(BookingNotFound):
        await service.get(uuid4())


async def test_list_applies_status_filter() -> None:
    service, repository, _ = make_service()
    await repository.add(build_booking(status=BookingStatus.PENDING))
    await repository.add(build_booking(status=BookingStatus.CONFIRMED))
    await repository.add(build_booking(status=BookingStatus.CONFIRMED))

    items, total = await service.list(status=BookingStatus.CONFIRMED, limit=10, offset=0)

    assert total == 2
    assert all(booking.status is BookingStatus.CONFIRMED for booking in items)


async def test_cancel_pending_deletes_and_commits() -> None:
    service, repository, _ = make_service()
    booking = build_booking(status=BookingStatus.PENDING)
    await repository.add(booking)

    await service.cancel(booking.id)

    assert booking.id not in repository.items
    assert repository.commits == 1


async def test_cancel_missing_raises_not_found() -> None:
    service, _, _ = make_service()

    with pytest.raises(BookingNotFound):
        await service.cancel(uuid4())


@pytest.mark.parametrize("status", [BookingStatus.CONFIRMED, BookingStatus.FAILED])
async def test_cancel_non_pending_rejected_and_kept(status: BookingStatus) -> None:
    service, repository, _ = make_service()
    booking = build_booking(status=status)
    await repository.add(booking)

    with pytest.raises(BookingNotCancellable):
        await service.cancel(booking.id)

    assert booking.id in repository.items
    assert repository.commits == 0


async def test_process_confirms_on_success() -> None:
    service, repository, _ = make_service(confirm=True)
    booking = build_booking(status=BookingStatus.PENDING)
    await repository.add(booking)

    await service.process(booking.id)

    assert booking.status is BookingStatus.CONFIRMED
    assert repository.commits == 1
    assert repository.locked_reads == [booking.id]  # читали с блокировкой строки


async def test_process_marks_failed_on_external_failure() -> None:
    service, repository, _ = make_service(confirm=False)
    booking = build_booking(status=BookingStatus.PENDING)
    await repository.add(booking)

    await service.process(booking.id)

    assert booking.status is BookingStatus.FAILED
    assert repository.commits == 1


@pytest.mark.parametrize("status", [BookingStatus.CONFIRMED, BookingStatus.FAILED])
async def test_process_is_idempotent_for_terminal_status(status: BookingStatus) -> None:
    service, repository, _ = make_service(confirm=False)
    booking = build_booking(status=status)
    await repository.add(booking)

    await service.process(booking.id)

    assert booking.status is status  # статус не изменился
    assert repository.commits == 0  # повторная обработка ничего не коммитит


async def test_process_noop_when_booking_missing() -> None:
    service, repository, _ = make_service()

    await service.process(uuid4())

    assert repository.commits == 0
