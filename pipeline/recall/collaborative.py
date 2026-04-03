"""协同过滤召回 — ItemCF"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.collaborative")


class CollaborativeRecall(PipelineStage):
    """基于物品协同过滤的召回。

    根据用户最近交互的物品，查找相似物品。
    相似度矩阵预计算，线上查表。
    """

    def __init__(self, top_k: int = 300, similarity_threshold: float = 0.5):
        self._top_k = top_k
        self._threshold = similarity_threshold
        self._similarity_matrix = None  # 预计算相似度矩阵

    def name(self) -> str:
        return "collaborative"

    def process(self, ctx: RecContext) -> RecContext:
        recent_items = ctx.user_features.get("recent_click_items", [])
        if not recent_items:
            return ctx

        try:
            # 从相似度矩阵中查找相似物品
            candidate_scores: dict[str, float] = {}
            for item_id in recent_items[:20]:  # 取最近 20 个交互物品
                similar = self._get_similar_items(item_id)
                for sim_id, sim_score in similar:
                    if sim_score >= self._threshold and sim_id not in recent_items:
                        candidate_scores[sim_id] = max(
                            candidate_scores.get(sim_id, 0), sim_score
                        )

            # 按相似度排序取 Top-K
            sorted_items = sorted(candidate_scores.items(), key=lambda x: -x[1])[:self._top_k]
            for item_id, score in sorted_items:
                ctx.candidates.append(Item(id=item_id, score=score, source="collaborative"))

        except Exception as e:
            logger.error(f"协同过滤召回异常", error=str(e))

        return ctx

    def _get_similar_items(self, item_id: str) -> list[tuple[str, float]]:
        """获取相似物品列表。生产环境从 Redis/内存加载。"""
        # TODO: 从预计算的相似度矩阵加载
        return []
