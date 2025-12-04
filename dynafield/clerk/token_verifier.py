import logging
from typing import Any, Dict, Optional

import jwt
from rediskit.redis.a_client import get_async_redis_connection

from .jwks_cache import cached_jwks_client

logger = logging.getLogger(__name__)


class TokenVerifier:
    """Production-grade token verification with multiple cache layers"""

    def __init__(self) -> None:
        self.jwks_client = cached_jwks_client
        self.token_cache_ttl = 300  # 5 minutes

    async def verify_and_decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token with multiple cache layers"""
        # Cache key for token verification result
        token_hash = self._get_token_hash(token)
        cache_key = f"token_verify:{token_hash}"
        redis_connection = await get_async_redis_connection()

        try:
            # Layer 1: Check if token verification is cached

            cached_payload = await redis_connection.get(cache_key)
            if cached_payload:
                logger.debug("Token verification result found in cache")
                return self._safe_json_loads(cached_payload)

            # Layer 2: Verify token with cached JWKS
            signing_key = await self.jwks_client.get_signing_key(token)

            payload = jwt.decode(
                token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False, "verify_exp": True, "verify_iss": True, "verify_signature": True}
            )

            # Cache the verification result
            await redis_connection.setex(cache_key, self.token_cache_ttl, self._safe_json_dumps(payload))

            logger.debug("Token verified and cached")
            return dict(payload)

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            # Cache expired tokens briefly to avoid repeated processing
            await redis_connection.setex(cache_key, 60, "expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            # Cache invalid tokens briefly
            await redis_connection.setex(cache_key, 60, "invalid")
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    @staticmethod
    def _get_token_hash(token: str) -> str:
        """Create a simple hash of the token for caching"""
        import hashlib

        return hashlib.md5(token.encode()).hexdigest()

    @staticmethod
    def _safe_json_dumps(data: Dict[str, Any]) -> str:
        """Safely serialize data to JSON"""
        import json

        return json.dumps(data, default=str)

    @staticmethod
    def _safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
        """Safely deserialize JSON data"""
        import json

        try:
            result = json.loads(data)
            return dict(result)
        except (json.JSONDecodeError, TypeError):
            return None


# Global instance
token_verifier = TokenVerifier()
