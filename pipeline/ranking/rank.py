"""精排 — DNN 精准预估 CTR/CVR"""

from __future__ import annotations

from pipeline.base import PipelineStage
from pipeline.context import sort_by_score, truncate_candidates
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("ranking.rank")


class RankStage(PipelineStage):
    """精排阶段：DNN 模型精准预估，千级 → 百级。"""

    def __init__(self, model_name: str = "dcn", max_candidates: int = 200, batch_size: int = 64):
        self._model_name = model_name
        self._max_candidates = max_candidates
        self._batch_size = batch_size
        self._model = None

    def name(self) -> str:
        return "rank"

    def process(self, ctx: RecContext) -> RecContext:
        if not ctx.candidates:
            return ctx

        features = self._extract_features(ctx)
        scores = self._batch_predict(features)

        for item, score in zip(ctx.candidates, scores):
            item.features["rank_score"] = score
            item.score = score

        sort_by_score(ctx)
        truncate_candidates(ctx, self._max_candidates)

        logger.debug(f"精排完成", input=len(features), output=len(ctx.candidates))
        return ctx

    def _extract_features(self, ctx: RecContext) -> list[dict]:
        """提取精排特征（含交叉特征）。"""
        features = []
        for item in ctx.candidates:
            feat = {
                **ctx.user_features,
                **item.features,
                **ctx.context_features,
            }
            # 添加交叉特征
            if "embedding" in ctx.user_features and "embedding" in item.features:
                feat["user_item_similarity"] = self._cosine_sim(
                    ctx.user_features["embedding"], item.features["embedding"]
                )
            features.append(feat)
        return features

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """计算余弦相似度。"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    def _batch_predict(self, features: list[dict]) -> list[float]:
        """分 batch 推理。"""
        if self._model is None:
            import numpy as np
            return np.random.random(len(features)).tolist()

        import numpy as np

        all_scores = []
        feature_arrays = []
        for feat in features:
            arr = [float(v) for v in feat.values() if isinstance(v, (int, float))]
            feature_arrays.append(arr)

        if not feature_arrays:
            return [0.0] * len(features)

        data = np.array(feature_arrays, dtype=np.float32)
        for i in range(0, len(data), self._batch_size):
            batch = data[i:i + self._batch_size]
            scores = self._model.predict(batch)
            all_scores.extend(scores.tolist())

        return all_scores
