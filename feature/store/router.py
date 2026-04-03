"""存储路由 — 根据特征定义路由到正确的存储后端"""

from __future__ import annotations

from typing import Any

from feature.registry.feature_def import FeatureDef, FeatureSource
from feature.registry.registry import FeatureRegistry
from feature.store.base import FeatureStore
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.store.router")


class StoreRouter:
    """存储路由：根据特征的 source 配置路由到对应存储后端。"""

    def __init__(self, registry: FeatureRegistry):
        self._registry = registry
        self._stores: dict[FeatureSource, FeatureStore] = {}

    def register_store(self, source: FeatureSource, store: FeatureStore) -> None:
        """注册存储后端。"""
        self._stores[source] = store
        logger.info(f"注册存储后端: {source.value}")

    def route(self, feature_name: str) -> FeatureStore | None:
        """路由到正确的存储后端。"""
        feature = self._registry.get(feature_name)
        if not feature:
            return None
        return self._stores.get(feature.source)

    async def get_features(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        """按特征名获取，自动路由到对应存储。"""
        result: dict[str, Any] = {}

        # 按 source 分组
        source_groups: dict[FeatureSource, list[str]] = {}
        for name in feature_names:
            feature = self._registry.get(name)
            if feature:
                source = feature.source
                source_groups.setdefault(source, []).append(name)

        # 并行查询各存储
        for source, names in source_groups.items():
            store = self._stores.get(source)
            if store:
                try:
                    data = await store.get(entity_id, names)
                    result.update(data)
                except Exception as e:
                    logger.error(f"特征获取失败: {source.value}", error=str(e))

        return result

    async def batch_get_features(
        self, entity_ids: list[str], feature_names: list[str]
    ) -> list[dict[str, Any]]:
        """批量获取特征。"""
        # 简化实现：逐个调用
        results = []
        for eid in entity_ids:
            data = await self.get_features(eid, feature_names)
            results.append(data)
        return results
