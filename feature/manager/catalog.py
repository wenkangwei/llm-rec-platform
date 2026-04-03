"""特征目录管理"""

from __future__ import annotations

from typing import Any

from feature.registry.feature_def import FeatureDef, FeatureStatus
from feature.registry.registry import FeatureRegistry
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.manager.catalog")


class FeatureCatalog:
    """特征目录管理：查询、浏览特征。"""

    def __init__(self, registry: FeatureRegistry):
        self._registry = registry

    def list_features(self, source: str | None = None, status: str | None = None) -> list[dict]:
        """列出所有特征。"""
        features = self._registry.list_all()
        if source:
            features = [f for f in features if f.source.value == source]
        if status:
            features = [f for f in features if f.status.value == status]
        return [
            {"slot_id": f.slot_id, "name": f.name, "dtype": f.dtype, "source": f.source.value, "status": f.status.value}
            for f in features
        ]

    def search_features(self, keyword: str) -> list[dict]:
        """搜索特征。"""
        features = self._registry.list_all()
        return [
            {"slot_id": f.slot_id, "name": f.name, "description": f.description}
            for f in features
            if keyword.lower() in f.name.lower() or keyword.lower() in f.description.lower()
        ]
