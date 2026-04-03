import redis.asyncio as redis
from ..core.config import settings

class SessionManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def create_session(self, user_id: int, token: str, ttl: int = 86400):
        # Store token for 24 hours (86400 seconds)
        await self.redis.setex(f"session:{token}", ttl, str(user_id))

    async def get_user_id(self, token: str):
        user_id = await self.redis.get(f"session:{token}")
        return int(user_id) if user_id else None

    async def invalidate_session(self, token: str):
        await self.redis.delete(f"session:{token}")
        # Could also blacklist refresh token
        await self.redis.setex(f"blacklist:{token}", 86400, "1")

    async def is_blacklisted(self, token: str):
        return await self.redis.exists(f"blacklist:{token}")

session_manager = SessionManager(settings.REDIS_URL)
