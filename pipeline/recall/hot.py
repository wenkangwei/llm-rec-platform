"""热门召回 — 全局/分类热门"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.hot")


class HotRecall(PipelineStage):
    """热门召回：返回全局或分类维度的热门内容。"""

    def __init__(self, top_k: int = 200, window_hours: int = 6):
        self._top_k = top_k
        self._window_hours = window_hours
        self._hot_items: list[tuple[str, float]] = []  # 内存缓存

    def name(self) -> str:
        return "hot"

    def process(self, ctx: RecContext) -> RecContext:
        try:
            items = self._get_hot_items()
            for item_id, score in items[:self._top_k]:
                ctx.candidates.append(Item(id=item_id, score=score, source="hot"))
        except Exception as e:
            logger.error(f"热门召回异常", error=str(e))

        return ctx

    def _get_hot_items(self) -> list[tuple[str, float]]:
        """获取热门物品列表。生产环境从 Redis 加载，开发环境用内存缓存。"""
        if self._hot_items:
            return self._hot_items
        try:
            from storage.redis import get_redis
            redis = get_redis()
            if redis:
                raw = redis.zrevrange("hot_items:global", 0, self._top_k - 1, withscores=True)
                if raw:
                    self._hot_items = [(item_id, score) for item_id, score in raw]
                    return self._hot_items
        except Exception as e:
            logger.debug(f"Redis 不可用", error=str(e))
        logger.warning("Redis 不可用，使用内存缓存（可能为空）")
        return []

    def update_hot_items(self, items: list[tuple[str, float]]) -> None:
        """更新热门物品缓存。"""
        self._hot_items = items
