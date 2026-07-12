import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def cache_get(key: str) -> Optional[Any]:
    """Returns the cached JSON value for a key, or None on a miss or if Redis is unavailable (never raises)."""
    try:
        raw = await redis_client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as e:
        logger.warning(f"Redis cache_get failed for '{key}': {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Caches a JSON-serializable value with a TTL in seconds. Silently no-ops if Redis is unavailable."""
    try:
        await redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"Redis cache_set failed for '{key}': {e}")


async def cache_delete_prefix(prefix: str) -> None:
    """Invalidates every cached key starting with prefix. Used after writes that could make cached reads stale."""
    try:
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=f"{prefix}*", count=200)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"Redis cache_delete_prefix failed for '{prefix}': {e}")
