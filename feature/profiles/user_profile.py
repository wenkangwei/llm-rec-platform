"""UserProfile — 用户画像"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UserSocialProfile:
    """用户社交画像。"""
    following_count: int = 0
    follower_count: int = 0
    mutual_follow_count: int = 0
    community_ids: list[str] = field(default_factory=list)
    interaction_strength: dict[str, float] = field(default_factory=dict)


@dataclass
class UserProfile:
    """用户画像。"""
    user_id: str
    interests: list[str] = field(default_factory=list)
    long_term_interests: list[float] = field(default_factory=list)
    short_term_interests: list[float] = field(default_factory=list)
    behavior_stats: dict[str, Any] = field(default_factory=dict)
    social: UserSocialProfile = field(default_factory=UserSocialProfile)
    embedding: Optional[list[float]] = None
    cold_start: bool = True
