import asyncio
import logging

from dynafield.clerk.jwks_cache import cached_jwks_client

logger = logging.getLogger(__name__)


async def refresh_jwks_periodically() -> None:
    """Background task to refresh JWKS periodically"""
    while True:
        try:
            await asyncio.sleep(3600)  # Wait 1 hour
            await cached_jwks_client.refresh_jwks_if_needed()
        except Exception as e:
            logger.error(f"Background JWKS refresh failed: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error


async def start_jwks_refresh_task() -> None:
    """Start the JWKS refresh task"""
    asyncio.create_task(refresh_jwks_periodically())
    logger.info("JWKS refresh task started")
