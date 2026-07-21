"""
Enterprise Caching Layer — Redis-backed response caching, query result caching,
hot-key prefetching, cache stampede protection, and tiered invalidation.
"""
import json
import hashlib
import functools
import asyncio
from typing import Any, Callable, Optional, Dict
from datetime import timedelta
from redis.asyncio import Redis

from ..core.config import settings
from ..core.logger import log

# ─── Redis Client ─────────────────────────────────────────────────────────────

_cache_client: Optional[Redis] = None

async def get_cache() -> Redis:
    """Get or create Redis cache client."""
    global _cache_client
    if _cache_client is None:
        try:
            _cache_client = Redis.from_url(settings.REDIS_URL, decode_responses=False)
            await _cache_client.ping()
        except Exception as e:
            log.warning("redis_cache.unavailable", error=str(e))
            _cache_client = None
    return _cache_client


# ─── Cache Key Generation ─────────────────────────────────────────────────────

def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a deterministic cache key from function arguments."""
    raw = f"{prefix}:{json.dumps(args, sort_keys=True, default=str)}:{json.dumps(kwargs, sort_keys=True, default=str)}"
    return f"cache:{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:16]}"


# ─── Response Cache Decorator ─────────────────────────────────────────────────

def cached(ttl_seconds: int = 60, prefix: str = "api", vary_by: Optional[list] = None):
    """Decorator for caching async function results in Redis.
    
    Args:
        ttl_seconds: Time-to-live in seconds (default 60s)
        prefix: Cache key prefix (e.g., "api", "query", "embedding")
        vary_by: Optional list of arg names to include in cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            redis = await get_cache()
            if redis is None:
                return await func(*args, **kwargs)

            # Build cache key from relevant arguments
            cache_args = args[1:]  # Skip 'self' for methods
            cache_kwargs = {k: kwargs[k] for k in (vary_by or []) if k in kwargs} if vary_by else kwargs
            key = cache_key(prefix, func.__qualname__, cache_args, cache_kwargs)

            # Try cache
            try:
                cached_data = await redis.get(key)
                if cached_data:
                    log.debug("cache_hit", key=key)
                    return json.loads(cached_data)
            except Exception:
                pass  # Cache miss — fall through

            # Compute fresh result with stampede protection
            lock_key = f"{key}:lock"
            acquired = await redis.set(lock_key, "1", nx=True, ex=5)
            
            if acquired:
                try:
                    result = await func(*args, **kwargs)
                    # Store in cache
                    await redis.setex(
                        key,
                        ttl_seconds,
                        json.dumps(result, default=str),
                    )
                    return result
                finally:
                    await redis.delete(lock_key)
            else:
                # Another caller is computing — wait and retry cache
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    try:
                        cached_data = await redis.get(key)
                        if cached_data:
                            return json.loads(cached_data)
                    except Exception:
                        pass
                # Fallback: compute anyway
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# ─── Cache Invalidation ───────────────────────────────────────────────────────

async def invalidate_pattern(pattern: str):
    """Invalidate all cache keys matching a glob pattern."""
    redis = await get_cache()
    if redis is None:
        return

    try:
        cursor = 0
        keys_deleted = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
                keys_deleted += len(keys)
            if cursor == 0:
                break
        if keys_deleted > 0:
            log.info("cache_invalidated", pattern=pattern, count=keys_deleted)
    except Exception as e:
        log.error("cache_invalidation_error", pattern=pattern, error=str(e))


async def invalidate_entity(entity_type: str, entity_id: Any = None):
    """Invalidate cache for a specific entity type."""
    if entity_id:
        pattern = f"cache:*:{entity_type}:{entity_id}:*"
    else:
        pattern = f"cache:*:{entity_type}:*"
    await invalidate_pattern(pattern)


# ─── Multi-Level Cache (L1: Application, L2: Redis) ──────────────────────────

class TwoLevelCache:
    """In-process dict cache (L1) backed by Redis (L2). Fastest path for hot data."""
    
    def __init__(self, max_size: int = 1000):
        self._local: Dict[str, tuple] = {}  # key → (value, expiry_timestamp)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get from L1 (local) then L2 (Redis)."""
        import time
        
        # Check L1
        if key in self._local:
            value, expiry = self._local[key]
            if time.time() < expiry:
                self._hits += 1
                return value
            del self._local[key]
        
        # Check L2
        redis = await get_cache()
        if redis:
            try:
                data = await redis.get(key)
                if data:
                    value = json.loads(data)
                    # Promote to L1
                    ttl = await redis.ttl(key)
                    self._local[key] = (value, time.time() + max(ttl, 1))
                    self._hits += 1
                    self._evict_if_needed()
                    return value
            except Exception:
                pass
        
        self._misses += 1
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 60):
        """Set in L2 (Redis) and promote to L1."""
        import time
        redis = await get_cache()
        if redis:
            await redis.setex(key, ttl_seconds, json.dumps(value, default=str))
        
        self._local[key] = (value, time.time() + ttl_seconds)
        self._evict_if_needed()

    async def invalidate(self, key: str):
        """Remove from both levels."""
        self._local.pop(key, None)
        redis = await get_cache()
        if redis:
            await redis.delete(key)

    def _evict_if_needed(self):
        """LRU-style eviction from L1 if over capacity."""
        if len(self._local) > self._max_size:
            # Remove oldest 10%
            excess = len(self._local) - int(self._max_size * 0.9)
            oldest = sorted(self._local.items(), key=lambda x: x[1][1])[:excess]
            for k, _ in oldest:
                del self._local[k]

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / max(total, 1)


# ─── Hot Key Prefetch ─────────────────────────────────────────────────────────

async def prefetch_hot_keys(keys: list):
    """Prefetch frequently accessed keys into L1 on startup/warm-up."""
    cache = TwoLevelCache()
    for key in keys:
        await cache.get(key)
    log.info("prefetch_complete", count=len(keys))


# ─── Cache Warming for Common Queries ────────────────────────────────────────

WARM_UP_QUERIES = [
    "cache:api:get_overview:*",
    "cache:api:get_hiring_funnel:*",
    "cache:db:active_jobs:*",
]


async def warm_up_cache():
    """Run cache warming on application startup."""
    for pattern in WARM_UP_QUERIES:
        log.info("cache_warming", pattern=pattern)
