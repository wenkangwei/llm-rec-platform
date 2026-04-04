"""实验数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ExperimentVariant:
    """实验分组。

    每个变体代表一种策略配置（如召回权重、排序模型等）。
    """
    name: str
    traffic_percent: float = 50.0  # 流量占比 0-100
    config: dict[str, Any] = field(default_factory=dict)  # 策略配置覆盖

    def __post_init__(self):
        if self.traffic_percent < 0 or self.traffic_percent > 100:
            raise ValueError(f"traffic_percent must be 0-100, got {self.traffic_percent}")


@dataclass
class Experiment:
    """A/B 实验。

    Attributes:
        id: 实验唯一 ID
        name: 实验名称
        variants: 实验分组列表（第一个为对照组）
        status: 实验状态
        metrics: 收集的指标
    """
    id: str
    name: str
    variants: list[ExperimentVariant] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metrics: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    created_at: float = 0.0
    started_at: float = 0.0
    ended_at: float = 0.0

    def __post_init__(self):
        if self.variants:
            total_traffic = sum(v.traffic_percent for v in self.variants)
            if abs(total_traffic - 100.0) > 0.01:
                raise ValueError(
                    f"Variant traffic percentages must sum to 100, got {total_traffic}"
                )

    def get_variant(self, variant_name: str) -> ExperimentVariant | None:
        """获取指定分组。"""
        for v in self.variants:
            if v.name == variant_name:
                return v
        return None
