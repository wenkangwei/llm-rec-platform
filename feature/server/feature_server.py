"""特征服务 — 提供给链路使用的在线特征获取"""

from __future__ import annotations

from typing import Any

from feature.platform import FeaturePlatform
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.server")


class FeatureServer:
    """在线特征服务：为推荐链路提供特征拉取。"""

    def __init__(self, platform: FeaturePlatform):
        self._platform = platform

    async def fetch_user_features(self, user_id: str, scene: str) -> dict[str, Any]:
        """拉取用户特征。"""
        features = await self._platform.get_features(user_id, [
            "age", "gender", "interests",
            "recent_click_items", "session_duration", "click_count_24h",
            "embedding",
        ])
        # 补充社交特征
        social_features = await self._platform.get_features(user_id, [
            "following_count", "follower_count", "community_ids",
        ])
        features.update(social_features)
        return features

    async def fetch_item_features(self, item_id: str) -> dict[str, Any]:
        """拉取物品特征。"""
        return await self._platform.get_features(item_id, [
            "content_type", "tags", "author_id",
            "like_count", "view_count", "engagement_rate",
            "embedding",
        ])

    async def fetch_context_features(self) -> dict[str, Any]:
        """拉取上下文特征。"""
        from datetime import datetime
        now = datetime.now()
        return {
            "hour_of_day": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "timestamp": now.timestamp(),
        }
