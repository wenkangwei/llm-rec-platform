"""FeatureLineage — 特征血缘追踪"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from feature.registry.feature_def import FeatureDef
from feature.registry.registry import FeatureRegistry
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.lineage")


@dataclass
class ImpactReport:
    """变更影响报告。"""
    feature_name: str
    upstream_count: int
    downstream_count: int
    upstream_features: list[str]
    downstream_features: list[str]
    risk_level: str = "low"  # low / medium / high


class FeatureLineage:
    """特征血缘追踪：通过 DFS 遍历依赖图。"""

    def __init__(self, registry: FeatureRegistry):
        self._registry = registry

    def get_upstream(self, feature_name: str) -> list[FeatureDef]:
        """获取某特征的所有上游依赖。"""
        feature = self._registry.get(feature_name)
        if not feature:
            return []
        result = []
        for dep_name in feature.depends_on:
            dep = self._registry.get(dep_name)
            if dep:
                result.append(dep)
                result.extend(self.get_upstream(dep_name))
        return result

    def get_downstream(self, feature_name: str) -> list[FeatureDef]:
        """获取某特征的所有下游影响。"""
        feature = self._registry.get(feature_name)
        if not feature:
            return []
        result = []
        for dep_name in feature.depended_by:
            dep = self._registry.get(dep_name)
            if dep:
                result.append(dep)
                result.extend(self.get_downstream(dep_name))
        return result

    def impact_analysis(self, feature_name: str) -> ImpactReport:
        """变更影响分析。"""
        upstream = self.get_upstream(feature_name)
        downstream = self.get_downstream(feature_name)

        downstream_count = len(downstream)
        risk = "low"
        if downstream_count >= 5:
            risk = "high"
        elif downstream_count >= 2:
            risk = "medium"

        return ImpactReport(
            feature_name=feature_name,
            upstream_count=len(upstream),
            downstream_count=downstream_count,
            upstream_features=[f.name for f in upstream],
            downstream_features=[f.name for f in downstream],
            risk_level=risk,
        )
