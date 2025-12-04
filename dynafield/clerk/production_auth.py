import logging
from typing import Any, Dict, Optional

from fastapi import Request

from dynafield.clerk.clerk_cache import clerk_cache
from dynafield.clerk.token_verifier import token_verifier

logger = logging.getLogger(__name__)


class MockRequest:
    def __init__(self, token: str) -> None:
        self.headers = {"authorization": f"Bearer {token}"}


async def get_current_user_production(request: Request | MockRequest) -> Optional[Dict[str, Any]]:
    """Production-grade user resolution with optimal caching"""
    auth_header = request.headers.get("authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    # Quick token validation
    if len(token) < 50:  # Basic JWT length check
        return None

    try:
        # Layer 1: Check if user data is cached by token
        cached_user = await clerk_cache.get_cached_user(token)
        if cached_user:
            logger.debug("User data found in token cache")
            return cached_user

        # Layer 2: Verify token with cached verification
        payload = await token_verifier.verify_and_decode_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            return None

        # Layer 3: Check if user data is cached by user ID
        cached_user_by_id = await clerk_cache.get_cached_user_by_id(user_id)
        if cached_user_by_id:
            # Also cache by token for future requests
            await clerk_cache.cache_user(token, cached_user_by_id)
            logger.debug("User data found in user ID cache")
            return cached_user_by_id

        user_data = {
            "clerk_id": user_id,
            "email": email,
            "first_name": payload.get("given_name", ""),
            "last_name": payload.get("family_name", ""),
            "username": payload.get("username", ""),
            "token_issued_at": payload.get("iat"),
            "token_expires_at": payload.get("exp"),
        }

        # Cache in both token and user ID caches
        await clerk_cache.cache_user(token, user_data)
        await clerk_cache.cache_user_by_id(user_id, user_data)

        return user_data

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return None


async def invalidate_user_cache(user_id: str) -> None:
    """Invalidate all caches for a user"""
    await clerk_cache.invalidate_user_cache(user_id)
    logger.info(f"Cache invalidated for user {user_id}")
