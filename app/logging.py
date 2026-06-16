import logging
import logging.handlers
from collections.abc import Sequence
from typing import Any

import structlog

from app.config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
APP_LOG_FILE = LOG_DIR / "app.log"
NOTIFICATIONS_LOG_FILE = LOG_DIR / "notifications.log"

MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

NOTIFICATIONS_LOGGER = "notifications"

_SHARED_PROCESSORS: Sequence[Any] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
)


def _rotating_handler(path: Any, formatter: logging.Formatter) -> logging.Handler:
    """Создаёт файловый обработчик с ротацией.

    Args:
        path: Путь к файлу лога.
        formatter: Форматтер записей.

    Returns:
        Обработчик логов с ротацией по размеру.
    """
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    return handler


def configure_logging(level: str = "INFO") -> None:
    """Настраивает structlog и stdlib-логирование.

    Args:
        level: Уровень логирования.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=list(_SHARED_PROCESSORS),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(_rotating_handler(APP_LOG_FILE, formatter))

    notifications = logging.getLogger(NOTIFICATIONS_LOGGER)
    notifications.handlers.clear()
    notifications.addHandler(_rotating_handler(NOTIFICATIONS_LOG_FILE, formatter))
    notifications.propagate = True
