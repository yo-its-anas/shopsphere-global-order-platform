"""Fault-tolerant Redis JSON cache adapter."""

from __future__ import annotations

import json
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisJsonCache:
    """Redis cache adapter that converts all cache failures into safe misses."""

    def __init__(
        self,
        url: str,
        password: str,
        socket_timeout: float,
    ) -> None:
        self._client: Redis = Redis.from_url(
            url,
            password=password,
            decode_responses=True,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
            health_check_interval=30,
        )

    async def get_json(self, key: str, family: str) -> object | None:
        try:
            value = await self._client.get(key)
        except RedisError:
            logger.warning(
                "cache_unavailable", extra={"event": "cache_unavailable", "cache_family": family}
            )
            return None
        if value is None:
            logger.info("cache_miss", extra={"event": "cache_miss", "cache_family": family})
            return None
        try:
            decoded: object = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            logger.warning(
                "cache_payload_invalid",
                extra={"event": "cache_payload_invalid", "cache_family": family},
            )
            await self.delete(key, family=family)
            return None
        logger.info("cache_hit", extra={"event": "cache_hit", "cache_family": family})
        return decoded

    async def set_json(self, key: str, value: object, ttl: int, family: str) -> None:
        try:
            await self._client.set(key, json.dumps(value, separators=(",", ":")), ex=ttl)
        except (RedisError, TypeError, ValueError):
            logger.warning(
                "cache_write_failed", extra={"event": "cache_write_failed", "cache_family": family}
            )

    async def delete(self, *keys: str, family: str) -> None:
        if not keys:
            return
        try:
            await self._client.unlink(*keys)
        except RedisError:
            logger.warning(
                "cache_invalidation_failed",
                extra={"event": "cache_invalidation_failed", "cache_family": family},
            )

    async def delete_prefix(self, prefix: str, family: str) -> None:
        try:
            batch: list[str] = []
            async for key in self._client.scan_iter(match=f"{prefix}*", count=100):
                batch.append(key)
                if len(batch) == 100:
                    await self._client.unlink(*batch)
                    batch.clear()
            if batch:
                await self._client.unlink(*batch)
        except RedisError:
            logger.warning(
                "cache_invalidation_failed",
                extra={"event": "cache_invalidation_failed", "cache_family": family},
            )

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except RedisError:
            logger.warning(
                "cache_close_failed",
                extra={"event": "cache_close_failed", "cache_family": "connection"},
            )
