from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.domain.models import BookingStatus
from app.domain.schemas import BookingCreate, BookingList, BookingRead
from app.rate_limit import RedisRateLimiter
from app.services.booking import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"], route_class=DishkaRoute)


def _client_id(request: Request) -> str:
    """Возвращает идентификатор клиента для лимитера.

    Args:
        request: HTTP-запрос.

    Returns:
        IP-адрес клиента или "unknown", если его нет.
    """
    return request.client.host if request.client else "unknown"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    request: Request,
    service: FromDishka[BookingService],
    limiter: FromDishka[RedisRateLimiter],
) -> BookingRead:
    """Создаёт бронь и ставит её на фоновое подтверждение.

    Args:
        data: Данные новой брони.
        request: HTTP-запрос.
        service: Сервис броней.
        limiter: Лимитер запросов.

    Returns:
        Созданная бронь в статусе pending.

    Raises:
        HTTPException: Превышен лимит запросов (429).
    """
    if not await limiter.is_allowed(identifier=_client_id(request=request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов",
        )
    booking = await service.create(data=data)
    return BookingRead.model_validate(booking)


@router.get("/{booking_id}")
async def get_booking(booking_id: UUID, service: FromDishka[BookingService]) -> BookingRead:
    """Возвращает бронь по идентификатору.

    Args:
        booking_id: Идентификатор брони.
        service: Сервис броней.

    Returns:
        Найденная бронь.
    """
    booking = await service.get(booking_id=booking_id)
    return BookingRead.model_validate(booking)


@router.get("")
async def list_bookings(
    service: FromDishka[BookingService],
    status_filter: Annotated[BookingStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BookingList:
    """Возвращает страницу броней с фильтром по статусу.

    Args:
        service: Сервис броней.
        status_filter: Фильтр по статусу или None для всех.
        limit: Размер страницы.
        offset: Смещение от начала выборки.

    Returns:
        Страница броней и общее количество по фильтру.
    """
    items, total = await service.list(status=status_filter, limit=limit, offset=offset)
    return BookingList(
        items=[BookingRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(booking_id: UUID, service: FromDishka[BookingService]) -> None:
    """Отменяет бронь, если она ещё в статусе pending.

    Args:
        booking_id: Идентификатор брони.
        service: Сервис броней.
    """
    await service.cancel(booking_id=booking_id)
