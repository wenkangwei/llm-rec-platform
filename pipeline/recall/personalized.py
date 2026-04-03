"""个性化召回 — 双塔向量召回"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.personalized")


class PersonalizedRecall(PipelineStage):
    """双塔模型个性化向量召回。

    1. 获取用户 embedding
    2. 在 Faiss 索引中 ANN 检索相似物品
    3. 返回 Top-K 候选
    """

    def __init__(self, top_k: int = 500):
        self._top_k = top_k
        self._faiss_index = None

    def name(self) -> str:
        return "personalized"

    def process(self, ctx: RecContext) -> RecContext:
        user_emb = ctx.user_features.get("embedding")

        if user_emb is None or self._faiss_index is None:
            # 降级：返回空结果
            logger.debug("用户 embedding 或 Faiss 索引不可用，跳过个性化召回")
            return ctx

        try:
            import numpy as np

            query = np.array([user_emb], dtype=np.float32)
            scores, ids = self._faiss_index.search(query, self._top_k)

            for score, item_id in zip(scores[0], ids[0]):
                if item_id >= 0:
                    ctx.candidates.append(Item(
                        id=str(item_id),
                        score=float(score),
                        source="personalized",
                    ))
        except Exception as e:
            logger.error(f"个性化召回异常", error=str(e))

        return ctx
