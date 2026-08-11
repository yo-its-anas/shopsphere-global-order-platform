"""Cache contracts, namespaced keys, and schema-safe response helpers."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
ModelType = TypeVar("ModelType", bound=BaseModel)


class CacheBackend(Protocol):
    async def get_json(self, key: str, family: str) -> object | None: ...

    async def set_json(self, key: str, value: object, ttl: int, family: str) -> None: ...

    async def delete(self, *keys: str, family: str) -> None: ...

    async def delete_prefix(self, prefix: str, family: str) -> None: ...

    async def close(self) -> None: ...


class NullCache:
    """No-op cache used when Redis is intentionally not configured."""

    async def get_json(self, key: str, family: str) -> object | None:
        return None

    async def set_json(self, key: str, value: object, ttl: int, family: str) -> None:
        return None

    async def delete(self, *keys: str, family: str) -> None:
        return None

    async def delete_prefix(self, prefix: str, family: str) -> None:
        return None

    async def close(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class CacheKeys:
    prefix: str
    environment: str

    @property
    def root(self) -> str:
        return f"{self.prefix}:{self.environment}"

    def category(self, category_id: UUID, scope: str) -> str:
        return f"{self.root}:category:{scope}:{category_id}"

    def category_list(self, scope: str, active: bool | None, offset: int, limit: int) -> str:
        return f"{self.root}:category-list:{scope}:{active}:{offset}:{limit}"

    def product(self, product_id: UUID, scope: str) -> str:
        return f"{self.root}:product:{scope}:{product_id}"

    def product_search(self, values: dict[str, object]) -> str:
        canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode(), usedforsecurity=False).hexdigest()[:32]
        return f"{self.root}:product-search:{digest}"

    def prices(self, product_id: UUID, scope: str, include_history: bool) -> str:
        return f"{self.root}:prices:{scope}:{product_id}:{include_history}"

    def availability(self, product_id: UUID, scope: str) -> str:
        return f"{self.root}:availability:{scope}:{product_id}"

    def inventory_item(self, product_id: UUID) -> str:
        return f"{self.root}:inventory-item:{product_id}"

    def inventory_list(self, state: object, offset: int, limit: int) -> str:
        return f"{self.root}:inventory-list:{state}:{offset}:{limit}"

    @property
    def inventory_statistics(self) -> str:
        return f"{self.root}:inventory-statistics"

    def family_prefix(self, family: str) -> str:
        return f"{self.root}:{family}:"


async def get_cached_model(
    cache: CacheBackend,
    key: str,
    family: str,
    model_type: type[ModelType],
) -> ModelType | None:
    value = await cache.get_json(key, family)
    if value is None:
        return None
    try:
        return model_type.model_validate(value)
    except ValidationError:
        logger.warning(
            "cache_schema_invalid", extra={"event": "cache_schema_invalid", "cache_family": family}
        )
        await cache.delete(key, family=family)
        return None


async def set_cached_model(
    cache: CacheBackend,
    key: str,
    family: str,
    model: BaseModel,
    ttl: int,
) -> None:
    await cache.set_json(key, model.model_dump(mode="json"), ttl, family)


def cache_scope(roles: frozenset[str]) -> str:
    return "operational" if roles.intersection({"support", "operations_admin"}) else "customer"
