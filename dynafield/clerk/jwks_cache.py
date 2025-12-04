import logging
import time
from typing import Any

from jwt import PyJWKClient
from rediskit.redis.a_client import get_async_redis_connection

from .. import config

logger = logging.getLogger(__name__)


class CachedJWKClient:
    """JWKS client with Redis caching and automatic refresh"""

    def __init__(self) -> None:
        self.jwks_client = PyJWKClient(
            config.CLERK_JWKS_URL,
            cache_keys=True,  # Enable built-in memory cache
            lifespan=3600,  # 1 hour cache
        )
        self.redis_cache_ttl = 86400  # 24 hours in Redis
        self.last_refresh = 0.0
        self.refresh_interval = 3600  # 1 hour

    async def get_signing_key(self, token: str) -> Any:
        """Get signing key with Redis caching"""
        try:
            # Try to get from Redis cache first
            redis_connection = await get_async_redis_connection()
            cache_key = "clerk_jwks"
            cached_jwks = await redis_connection.get(cache_key)

            if cached_jwks:
                logger.debug("JWKS found in Redis cache")
                # The PyJWKClient will use its internal cache if available
                return self.jwks_client.get_signing_key_from_jwt(token)

            # If not in Redis, use the client (which has its own cache)
            # and cache the fact that we've fetched it
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Cache the JWKS availability in Redis (we don't cache the actual keys,
            # just that we've successfully fetched them)
            await redis_connection.setex(cache_key, self.redis_cache_ttl, "available")

            return signing_key

        except Exception as e:
            logger.error(f"Failed to get signing key: {e}")
            raise

    async def refresh_jwks_if_needed(self) -> None:
        """Force refresh JWKS if cache is stale"""
        current_time = time.time()
        if current_time - self.last_refresh > self.refresh_interval:
            try:
                redis_connection = await get_async_redis_connection()
                # Clear the internal cache to force refresh
                if hasattr(self.jwks_client, "_cache"):
                    self.jwks_client._cache.clear()

                # Also clear Redis cache marker
                await redis_connection.delete("clerk_jwks")

                self.last_refresh = current_time
                logger.info("JWKS cache refreshed")

            except Exception as e:
                logger.error(f"Failed to refresh JWKS cache: {e}")


# Global instance
cached_jwks_client = CachedJWKClient()
