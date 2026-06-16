from collections.abc import AsyncIterator

import pytest
from app.rate_limit import RedisRateLimiter
from fakeredis import aioredis
from redis.asyncio import Redis


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    """Поднимает поддельный Redis с поддержкой Lua.

    Yields:
        Клиент fakeredis.
    """
    client: Redis = aioredis.FakeRedis()
    yield client
    await client.aclose()


async def test_allows_up_to_limit_then_blocks(redis: Redis) -> None:
    limiter = RedisRateLimiter(redis=redis, times=3, seconds=60)

    results = [await limiter.is_allowed("1.2.3.4") for _ in range(5)]

    assert results == [True, True, True, False, False]


async def test_limits_are_isolated_per_identifier(redis: Redis) -> None:
    limiter = RedisRateLimiter(redis=redis, times=1, seconds=60)

    assert await limiter.is_allowed("a") is True
    assert await limiter.is_allowed("a") is False
    assert await limiter.is_allowed("b") is True


async def test_sets_ttl_on_first_request(redis: Redis) -> None:
    limiter = RedisRateLimiter(redis=redis, times=2, seconds=42)

    await limiter.is_allowed("1.2.3.4")

    assert await redis.ttl("rate-limit:1.2.3.4") == 42


async def test_window_resets_after_expiry(redis: Redis) -> None:
    limiter = RedisRateLimiter(redis=redis, times=1, seconds=60)
    assert await limiter.is_allowed("1.2.3.4") is True
    assert await limiter.is_allowed("1.2.3.4") is False

    await redis.delete("rate-limit:1.2.3.4")

    assert await limiter.is_allowed("1.2.3.4") is True
