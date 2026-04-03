"""FeatureDef — 特征定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeatureSource(str, Enum):
    REDIS = "redis"
    MYSQL = "mysql"
    HIVE = "hive"
    FAISS = "faiss"
    CONTEXT = "context"
    DERIVED = "derived"
    COMPOSITE = "composite"


class FeatureStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class ValueType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    SCALAR = "scalar"


@dataclass
class FeatureDef:
    """特征定义。"""
    slot_id: str                          # 全局唯一标识
    name: str                             # 特征名称
    dtype: str = "float"                  # int, float, string, array, map
    value_type: ValueType = ValueType.SCALAR
    dimension: int = 0                    # 向量维度（embedding 用）
    source: FeatureSource = FeatureSource.REDIS
    source_config: dict[str, Any] = field(default_factory=dict)
    dsl: str | None = None                # 衍生特征 DSL 表达式
    composite_of: list[str] = field(default_factory=list)  # 组合特征子特征
    depends_on: list[str] = field(default_factory=list)     # 上游依赖
    depended_by: list[str] = field(default_factory=list)    # 下游被依赖
    status: FeatureStatus = FeatureStatus.ACTIVE
    version: str = "v1"
    owner: str = ""
    description: str = ""
