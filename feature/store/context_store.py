"""上下文特征存储 — 请求级特征（时间、设备等）"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from feature.store.base import FeatureStore


class ContextFeatureStore(FeatureStore):
    """上下文特征存储：从请求上下文中提取特征，不需要外部存储。"""

    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        now = datetime.now()
        ctx_features = {
            "hour_of_day": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "timestamp": now.timestamp(),
        }
        return {k: v for k, v in ctx_features.items() if k in feature_names}

    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        result = await self.get("", feature_names)
        return [result.copy() for _ in entity_ids]

    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        pass  # 上下文特征只读

    async def health_check(self) -> bool:
        return True
