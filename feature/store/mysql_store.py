"""MySQL 特征存储 — 准实时特征（用户画像、物品属性）"""

from __future__ import annotations

from typing import Any

from feature.store.base import FeatureStore
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.store.mysql")


class MySQLFeatureStore(FeatureStore):
    """MySQL 特征存储：准实时特征。"""

    def __init__(self, mysql_store, table: str = "user_features"):
        self._mysql = mysql_store
        self._table = table

    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        row = await self._mysql.fetch_one(
            self._table,
            conditions={"entity_id": entity_id},
            columns=feature_names,
        )
        return row or {}

    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        results = []
        for eid in entity_ids:
            row = await self.get(eid, feature_names)
            results.append(row)
        return results

    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        # UPSERT
        cols = ", ".join(features.keys())
        vals = ", ".join(f"%s" for _ in features)
        updates = ", ".join(f"{k} = %s" for k in features.keys())
        sql = f"INSERT INTO {self._table} (entity_id, {cols}) VALUES (%s, {vals}) ON DUPLICATE KEY UPDATE {updates}"
        values = [entity_id] + list(features.values()) + list(features.values())
        await self._mysql.execute(sql, tuple(values))

    async def health_check(self) -> bool:
        return self._mysql._pool is not None
