"""ItemProfile — 物品画像"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ItemAuthor:
    author_id: str
    follower_count: int = 0
    avg_engagement: float = 0.0


@dataclass
class ItemSocialStats:
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0
    engagement_rate: float = 0.0


@dataclass
class ItemProfile:
    """物品画像。"""
    item_id: str
    content_type: str = "article"  # 图文/视频/post
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    author: ItemAuthor = field(default_factory=lambda: ItemAuthor(author_id=""))
    stats: ItemSocialStats = field(default_factory=ItemSocialStats)
    embedding: Optional[list[float]] = None
    decay_score: float = 1.0  # 时间衰减分
