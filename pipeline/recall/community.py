"""社区召回 — 基于社区归属"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.community")


class CommunityRecall(PipelineStage):
    """社区召回：推荐用户活跃社区的热门内容。"""

    def __init__(self, top_k: int = 200):
        self._top_k = top_k

    def name(self) -> str:
        return "community"

    def process(self, ctx: RecContext) -> RecContext:
        community_ids = ctx.user_features.get("community_ids", [])
        if not community_ids:
            return ctx

        try:
            items = self._fetch_community_hot(community_ids)
            for item_id, score, community_id in items[:self._top_k]:
                ctx.candidates.append(Item(
                    id=item_id,
                    score=score,
                    source="community",
                    metadata={"community_id": community_id},
                ))
        except Exception as e:
            logger.error(f"社区召回异常", error=str(e))

        return ctx

    def _fetch_community_hot(self, community_ids: list[str]) -> list[tuple[str, float, str]]:
        """获取社区热门内容。"""
        try:
            from storage.redis import get_redis
            redis = get_redis()
            if redis:
                results = []
                for cid in community_ids:
                    raw = redis.zrevrange(f"community_hot:{cid}", 0, self._top_k - 1, withscores=True)
                    if raw:
                        results.extend((item_id, score, cid) for item_id, score in raw)
                return sorted(results, key=lambda x: -x[1])
        except Exception:
            pass
        return []
