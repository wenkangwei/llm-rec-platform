"""FeatureGroupDef — 特征组定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from feature.registry.feature_def import FeatureDef


@dataclass
class FeatureGroupDef:
    """特征组：将相关特征聚合为一组，方便批量获取。"""
    name: str
    entity_type: str  # user / item / context
    features: list[FeatureDef] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def get_feature(self, name: str) -> FeatureDef | None:
        """按名称获取特征。"""
        for f in self.features:
            if f.name == name:
                return f
        return None

    def get_active_features(self) -> list[FeatureDef]:
        """获取所有活跃特征。"""
        from feature.registry.feature_def import FeatureStatus
        return [f for f in self.features if f.status == FeatureStatus.ACTIVE]

    def add_feature(self, feature: FeatureDef) -> None:
        """添加特征。"""
        self.features.append(feature)
