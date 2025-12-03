import json
import logging
from typing import Any, Dict, Optional

from jwt import PyJWKClient
from rediskit.redis.a_client import get_async_redis_connection

from dynafield import config

logger = logging.getLogger(__name__)

# JWKS client for token verification
jwks_client = PyJWKClient(config.CLERK_JWKS_URL)


class ClerkTokenCache:
    def __init__(self) -> None:
        self.jwks_client = jwks_client
        self.token_cache_ttl = 300  # 5 minutes
        self.user_cache_ttl = 3600  # 1 hour

    @staticmethod
    async def get_cached_user(token: str) -> Optional[Dict[str, Any]]:
        """Get user from cache if token is valid and cached"""
        try:
            # Check if token is cached
            redis_client = await get_async_redis_connection()
            cache_key = f"clerk_token:{token}"
            cached_user = await redis_client.get(cache_key)

            if cached_user:
                logger.debug("User data found in cache")
                data = json.loads(cached_user)
                return dict(data)

            return None
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None

    async def cache_user(self, token: str, user_data: Dict[str, Any]) -> None:
        """Cache user data with token as key"""
        try:
            redis_connection = await get_async_redis_connection()
            cache_key = f"clerk_token:{token}"
            await redis_connection.setex(cache_key, self.token_cache_ttl, json.dumps(user_data))
            logger.debug("User data cached successfully")
        except Exception as e:
            logger.error(f"Error caching user data: {e}")

    @staticmethod
    async def get_cached_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by user ID (for tenant resolution)"""
        try:
            redis_connection = await get_async_redis_connection()
            cache_key = f"clerk_user:{user_id}"
            cached_user = await redis_connection.get(cache_key)

            if cached_user:
                logger.debug(f"User {user_id} found in cache")
                data = json.loads(cached_user)
                return dict(data)

            return None
        except Exception as e:
            logger.error(f"Error reading user from cache: {e}")
            return None

    async def cache_user_by_id(self, user_id: str, user_data: Dict[str, Any]) -> None:
        """Cache user data by user ID"""
        try:
            redis_connection = await get_async_redis_connection()
            cache_key = f"clerk_user:{user_id}"
            await redis_connection.setex(cache_key, self.user_cache_ttl, json.dumps(user_data))
            logger.debug(f"User {user_id} cached successfully")
        except Exception as e:
            logger.error(f"Error caching user by ID: {e}")

    @staticmethod
    async def invalidate_user_cache(user_id: str) -> None:
        """Invalidate cache for a specific user"""
        try:
            redis_connection = await get_async_redis_connection()
            cache_key = f"clerk_user:{user_id}"
            await redis_connection.delete(cache_key)
            logger.debug(f"Cache invalidated for user {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")


# Global instance
clerk_cache = ClerkTokenCache()
