"""推荐上下文数据结构 — 贯穿整个链路的上下文对象"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageMetrics:
    """单阶段执行指标。"""
    stage_name: str
    latency_ms: float = 0.0
    input_count: int = 0
    output_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Item:
    """候选物品。"""
    id: str
    score: float = 0.0
    source: str = ""  # 来源通道
    features: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecContext:
    """推荐请求上下文，贯穿整个链路。

    每个模块只读写 ctx 中属于自己的字段。
    """
    request_id: str
    user_id: str
    scene: str  # home_feed / search_feed / follow_feed / community_feed
    candidates: list[Item] = field(default_factory=list)
    user_features: dict[str, Any] = field(default_factory=dict)
    context_features: dict[str, Any] = field(default_factory=dict)
    stage_metrics: list[StageMetrics] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    # 搜索场景特有
    query: str | None = None

    # 分页
    page: int = 0
    page_size: int = 20

    # 降级标记
    degraded: bool = False
    degraded_stages: list[str] = field(default_factory=list)

    # 实验分流
    experiment_id: str = ""
    variant_name: str = ""
    experiment_overrides: dict[str, Any] = field(default_factory=dict)
