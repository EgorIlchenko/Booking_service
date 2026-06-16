from redis.asyncio import Redis

_INCREMENT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class RedisRateLimiter:
    """Лимитер запросов на фиксированном окне поверх Redis."""

    def __init__(self, redis: Redis, *, times: int, seconds: int) -> None:
        """Сохраняет клиент Redis и параметры окна.

        Args:
            redis: Клиент Redis.
            times: Сколько запросов разрешено за окно.
            seconds: Длина окна в секундах.
        """
        self._redis = redis
        self._times = times
        self._seconds = seconds
        self._increment = redis.register_script(_INCREMENT)

    async def is_allowed(self, identifier: str) -> bool:
        """Учитывает запрос и сообщает, не превышен ли лимит.

        Args:
            identifier: Ключ клиента, например IP-адрес.

        Returns:
            True, если запрос укладывается в лимит, иначе False.
        """
        key = f"rate-limit:{identifier}"
        current = await self._increment(keys=[key], args=[self._seconds])
        return int(current) <= self._times
