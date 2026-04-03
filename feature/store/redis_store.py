"""Redis 特征存储 — 实时特征"""

from __future__ import annotations

from typing import Any

from feature.store.base import FeatureStore
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.store.redis")


class RedisFeatureStore(FeatureStore):
    """Redis 特征存储：实时特征（用户行为统计、session 特征等）。"""

    def __init__(self, redis_store):
        self._redis = redis_store

    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        data = await self._redis.get(f"feat:{entity_id}")
        if not data:
            return {}
        return {k: v for k, v in data.items() if k in feature_names}

    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        results = await self._redis.mget([f"feat:{eid}" for eid in entity_ids])
        return [
            {k: v for k, v in (data or {}).items() if k in feature_names}
            for data in results
        ]

    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        await self._redis.set(f"feat:{entity_id}", features, ttl=ttl)

    async def health_check(self) -> bool:
        return self._redis._pool is not None
