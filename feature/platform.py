"""FeaturePlatform — 特征平台统一 API 入口"""

from __future__ import annotations

from typing import Any

from feature.registry.registry import FeatureRegistry
from feature.store.router import StoreRouter
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.platform")


class FeaturePlatform:
    """特征平台唯一外部入口。

    调用方无需关心数据源，通过统一 API 获取特征。
    """

    def __init__(self, registry: FeatureRegistry, router: StoreRouter):
        self._registry = registry
        self._router = router

    async def get_features(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        """获取实体的一组特征。"""
        return await self._router.get_features(entity_id, feature_names)

    async def get_feature_group(self, entity_id: str, group_name: str) -> dict[str, Any]:
        """获取特征组的所有活跃特征。"""
        group = self._registry.get_group(group_name)
        if not group:
            return {}
        names = [f.name for f in group.get_active_features()]
        return await self.get_features(entity_id, names)

    async def batch_get_features(
        self, entity_ids: list[str], feature_names: list[str]
    ) -> list[dict[str, Any]]:
        """批量获取多个实体的特征。"""
        return await self._router.batch_get_features(entity_ids, feature_names)

    def get_registry(self) -> FeatureRegistry:
        """获取特征注册中心。"""
        return self._registry
