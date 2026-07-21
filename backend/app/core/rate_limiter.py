"""
Global rate limiter using Redis token bucket algorithm (async).
Used for Gemini API or other external services.
"""
import asyncio
import time
from typing import Optional
from ..core.config import settings


class RedisTokenBucket:
    """
    Async Redis-based token bucket rate limiter.
    """

    def __init__(self, redis_client, key_prefix: str = "rate_limit"):
        self.redis = redis_client  # redis.asyncio.Redis
        self.prefix = key_prefix

    async def check_rate_limit(
        self, org_id: int, limit: int = 10, period: int = 60
    ) -> bool:
        """
        Standard token bucket. Returns True if bucket has tokens.
        Default: 10 requests per 60 seconds (1 minute).
        """
        key = f"{self.prefix}:{org_id}"
        now = time.time()

        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local period = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local leak_rate = limit / period

        local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
        local tokens = tonumber(bucket[1]) or limit
        local last_update = tonumber(bucket[2]) or now

        local delta = math.max(0, now - last_update)
        tokens = math.min(limit, tokens + (delta * leak_rate))

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', key, period * 2)
            return 1
        else
            return 0
        end
        """
        allowed = await self.redis.eval(lua_script, 1, key, limit, period, now)
        return bool(allowed)

    async def wait_for_token(
        self,
        org_id: int,
        limit: int = 10,
        period: int = 60,
        timeout: int = 30,
    ) -> bool:
        """
        Blocking wait until a token is available or timeout occurs.
        Uses asyncio.sleep for non-blocking waits.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.check_rate_limit(org_id, limit, period):
                return True
            await asyncio.sleep(1)
        return False
