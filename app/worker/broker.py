from taskiq import AsyncBroker
from taskiq.middlewares import SmartRetryMiddleware
from taskiq_redis import RedisStreamBroker

from app.config import get_settings


def create_broker() -> AsyncBroker:
    """Создаёт TaskIQ-брокер с ретраями.

    Returns:
        Настроенный async-брокер на Redis.
    """
    broker: AsyncBroker = RedisStreamBroker(url=get_settings().redis_url)
    broker.add_middlewares(
        SmartRetryMiddleware(
            default_retry_count=3,
            default_delay=1.0,
            use_delay_exponent=True,
            max_delay_exponent=60.0,
        )
    )
    return broker


broker = create_broker()
