"""FeatureRegistry — 特征注册中心"""

from __future__ import annotations

from typing import Any

from feature.registry.feature_def import FeatureDef, FeatureSource, FeatureStatus
from feature.registry.group_def import FeatureGroupDef
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.registry")


class FeatureRegistry:
    """特征注册中心：管理所有特征定义、分组和查找。"""

    def __init__(self):
        self._features: dict[str, FeatureDef] = {}     # slot_id → FeatureDef
        self._name_index: dict[str, str] = {}           # name → slot_id
        self._groups: dict[str, FeatureGroupDef] = {}   # group_name → GroupDef

    def register(self, feature: FeatureDef) -> None:
        """注册特征。"""
        self._features[feature.slot_id] = feature
        self._name_index[feature.name] = feature.slot_id
        logger.info(f"特征注册: {feature.name}", slot_id=feature.slot_id)

    def register_group(self, group: FeatureGroupDef) -> None:
        """注册特征组。"""
        self._groups[group.name] = group
        for f in group.features:
            self.register(f)
        logger.info(f"特征组注册: {group.name}", features=len(group.features))

    def get(self, name: str) -> FeatureDef | None:
        """按名称获取特征。"""
        slot_id = self._name_index.get(name)
        if slot_id:
            return self._features.get(slot_id)
        return self._features.get(name)

    def get_group(self, group_name: str) -> FeatureGroupDef | None:
        """获取特征组。"""
        return self._groups.get(group_name)

    def get_by_source(self, source: FeatureSource) -> list[FeatureDef]:
        """按数据源筛选特征。"""
        return [f for f in self._features.values() if f.source == source]

    def get_active_features(self) -> list[FeatureDef]:
        """获取所有活跃特征。"""
        return [f for f in self._features.values() if f.status == FeatureStatus.ACTIVE]

    def list_all(self) -> list[FeatureDef]:
        """列出所有特征。"""
        return list(self._features.values())

    def list_groups(self) -> list[str]:
        """列出所有特征组名称。"""
        return list(self._groups.keys())

    def unregister(self, name: str) -> None:
        """注销特征。"""
        slot_id = self._name_index.pop(name, None)
        if slot_id:
            del self._features[slot_id]

    def load_from_config(self, config: dict[str, Any]) -> None:
        """从配置文件批量加载特征。"""
        for group_name, group_data in config.items():
            if isinstance(group_data, dict) and "fields" in group_data:
                group = FeatureGroupDef(
                    name=group_name,
                    entity_type=group_data.get("type", "user"),
                )
                for f_cfg in group_data["fields"]:
                    feature = FeatureDef(
                        slot_id=f"{group_name}.{f_cfg['name']}",
                        name=f_cfg["name"],
                        dtype=f_cfg.get("dtype", "float"),
                        dimension=f_cfg.get("dimension", 0),
                        source=FeatureSource(group_data.get("source", "redis")),
                    )
                    group.add_feature(feature)
                self.register_group(group)
