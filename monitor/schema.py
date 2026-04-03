"""监控数据结构 — PipelineTrace / ItemTrace / RecallCoverage"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StageTrace:
    """单阶段追踪。"""
    stage_name: str
    latency_ms: float
    input_count: int
    output_count: int
    error: str = ""


@dataclass
class ItemTrace:
    """物品在各阶段的追踪。"""
    item_id: str
    scores: dict[str, float] = field(default_factory=dict)      # {stage_name: score}
    positions: dict[str, int] = field(default_factory=dict)      # {stage_name: position}
    filtered_out_at: str = ""     # 被过滤的阶段
    filter_reason: str = ""
    recall_sources: list[str] = field(default_factory=list)


@dataclass
class RecallCoverage:
    """召回通道覆盖率。"""
    source: str
    recalled_count: int
    survived_count: int
    final_exposed: int


@dataclass
class PipelineTrace:
    """完整链路追踪。"""
    trace_id: str
    request_id: str
    user_id: str
    scene: str
    total_latency_ms: float = 0.0
    stages: list[StageTrace] = field(default_factory=list)
    item_traces: list[ItemTrace] = field(default_factory=list)
    recall_coverages: list[RecallCoverage] = field(default_factory=list)
    timestamp: float = 0.0
