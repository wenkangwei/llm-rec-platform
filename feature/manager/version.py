"""特征版本管理"""

from __future__ import annotations

from feature.registry.feature_def import FeatureDef
from feature.registry.registry import FeatureRegistry
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.manager.version")


class FeatureVersionManager:
    """特征版本管理：追踪版本变更历史。"""

    def __init__(self, registry: FeatureRegistry):
        self._registry = registry
        self._history: list[dict] = []

    def record_change(self, feature_name: str, old_version: str, new_version: str, reason: str) -> None:
        """记录版本变更。"""
        self._history.append({
            "feature_name": feature_name,
            "old_version": old_version,
            "new_version": new_version,
            "reason": reason,
        })
        logger.info(f"特征版本变更: {feature_name}", old=old_version, new=new_version)

    def get_history(self, feature_name: str | None = None) -> list[dict]:
        """获取版本历史。"""
        if feature_name:
            return [h for h in self._history if h["feature_name"] == feature_name]
        return self._history
