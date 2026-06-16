import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import BookingNotCancellable, BookingNotFound

logger = structlog.get_logger(__name__)


async def _booking_not_found(_request: Request, exc: Exception) -> JSONResponse:
    """Преобразует отсутствие брони в 404.

    Args:
        _request: Запрос.
        exc: Доменное исключение.

    Returns:
        Ответ 404 с описанием ошибки.
    """
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _booking_not_cancellable(_request: Request, exc: Exception) -> JSONResponse:
    """Преобразует запрет отмены в 409.

    Args:
        _request: Запрос.
        exc: Доменное исключение.

    Returns:
        Ответ 409 с описанием ошибки.
    """
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
    """Логирует необработанное исключение и отдаёт 500.

    Args:
        _request: Запрос.
        exc: Необработанное исключение.

    Returns:
        Ответ 500 с обобщённым описанием.
    """
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений.

    Args:
        app: Приложение FastAPI.
    """
    app.add_exception_handler(BookingNotFound, _booking_not_found)
    app.add_exception_handler(BookingNotCancellable, _booking_not_cancellable)
    app.add_exception_handler(Exception, _unhandled)
