"""运营召回 — 运营精选/置顶"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.operator")


class OperatorRecall(PipelineStage):
    """运营召回：返回运营配置的精选/置顶内容。"""

    def __init__(self, top_k: int = 50):
        self._top_k = top_k
        self._pinned_items: list[tuple[str, float]] = []

    def name(self) -> str:
        return "operator"

    def process(self, ctx: RecContext) -> RecContext:
        try:
            for item_id, score in self._pinned_items[:self._top_k]:
                ctx.candidates.append(Item(
                    id=item_id,
                    score=score,
                    source="operator",
                    metadata={"pinned": True},
                ))
        except Exception as e:
            logger.error(f"运营召回异常", error=str(e))

        return ctx

    def update_pinned(self, items: list[tuple[str, float]]) -> None:
        """更新运营置顶内容。"""
        self._pinned_items = items
        logger.info(f"运营置顶更新: {len(items)} 条")
