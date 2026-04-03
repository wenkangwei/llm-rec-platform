"""社交召回 — 基于关注关系"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.social")


class SocialRecall(PipelineStage):
    """社交召回：推荐关注者最近交互的内容。"""

    def __init__(self, top_k: int = 200, recent_hours: int = 24):
        self._top_k = top_k
        self._recent_hours = recent_hours

    def name(self) -> str:
        return "social"

    def process(self, ctx: RecContext) -> RecContext:
        following_ids = ctx.user_features.get("following_ids", [])
        if not following_ids:
            return ctx

        try:
            # 获取关注者最近交互的内容
            items = self._fetch_following_interactions(following_ids)
            for item_id, score, interaction_type in items[:self._top_k]:
                ctx.candidates.append(Item(
                    id=item_id,
                    score=score,
                    source="social",
                    metadata={"interaction_type": interaction_type},
                ))
        except Exception as e:
            logger.error(f"社交召回异常", error=str(e))

        return ctx

    def _fetch_following_interactions(self, following_ids: list[str]) -> list[tuple[str, float, str]]:
        """获取关注者最近交互的内容。生产环境从 Redis 查询。"""
        # TODO: 从 Redis 获取关注者最近交互内容
        return []
