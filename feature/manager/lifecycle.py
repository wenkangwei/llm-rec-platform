"""特征生命周期管理"""

from __future__ import annotations

from feature.registry.feature_def import FeatureDef, FeatureStatus
from feature.registry.registry import FeatureRegistry
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.manager.lifecycle")


class FeatureLifecycle:
    """特征生命周期管理：draft → active → deprecated。"""

    def __init__(self, registry: FeatureRegistry):
        self._registry = registry

    def activate(self, feature_name: str) -> bool:
        """将特征从 draft 激活为 active。"""
        feature = self._registry.get(feature_name)
        if feature and feature.status == FeatureStatus.DRAFT:
            feature.status = FeatureStatus.ACTIVE
            logger.info(f"特征激活: {feature_name}")
            return True
        return False

    def deprecate(self, feature_name: str) -> bool:
        """将特征标记为 deprecated。"""
        feature = self._registry.get(feature_name)
        if feature and feature.status == FeatureStatus.ACTIVE:
            feature.status = FeatureStatus.DEPRECATED
            logger.info(f"特征废弃: {feature_name}")
            return True
        return False

    def reactivate(self, feature_name: str) -> bool:
        """重新激活废弃特征。"""
        feature = self._registry.get(feature_name)
        if feature and feature.status == FeatureStatus.DEPRECATED:
            feature.status = FeatureStatus.ACTIVE
            logger.info(f"特征重新激活: {feature_name}")
            return True
        return False
