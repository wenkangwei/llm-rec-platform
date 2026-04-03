"""用户行为事件 — 异步日志落盘用"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TrackEventV2:
    """用户行为事件（内部使用，比 HTTP Schema 更丰富）。"""
    event_id: str
    user_id: str
    item_id: str
    action: str  # expose, click, like, share, comment, dwell
    scene: str
    request_id: str
    timestamp: float  # Unix timestamp

    # 上下文
    page: int = 0
    position: int = 0
    device_type: str = ""

    # 行为详情
    dwell_time_sec: Optional[float] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingLogEntry:
    """训练日志条目。"""
    trace_id: str

    # 特征
    user_features: dict[str, Any] = field(default_factory=dict)
    item_features: dict[str, Any] = field(default_factory=dict)
    social_features: dict[str, Any] = field(default_factory=dict)
    context_features: dict[str, Any] = field(default_factory=dict)
    cross_features: dict[str, Any] = field(default_factory=dict)

    # 模型分数
    prerank_score: float = 0.0
    rank_score: float = 0.0
    rank_position: int = 0

    # 标签（延迟回填）
    label_clicked: Optional[bool] = None
    label_liked: Optional[bool] = None
    label_shared: Optional[bool] = None
    label_commented: Optional[bool] = None
    dwell_time_sec: Optional[float] = None
