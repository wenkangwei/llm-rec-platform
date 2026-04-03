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
        """获取热门物品列表。生产环境从 Redis 加载。"""
        if self._hot_items:
            return self._hot_items
        # TODO: 从 Redis 加载实时热度排行
        return []

    def update_hot_items(self, items: list[tuple[str, float]]) -> None:
        """更新热门物品缓存。"""
        self._hot_items = items
