"""粗排 — LightGBM 快速过滤"""

from __future__ import annotations

from pipeline.base import PipelineStage
from pipeline.context import sort_by_score, truncate_candidates
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("ranking.prerank")


class PreRankStage(PipelineStage):
    """粗排阶段：LightGBM 快速打分，万级 → 千级。"""

    def __init__(self, max_candidates: int = 1000, score_threshold: float = 0.1):
        self._max_candidates = max_candidates
        self._threshold = score_threshold
        self._model = None

    def name(self) -> str:
        return "prerank"

    def process(self, ctx: RecContext) -> RecContext:
        if not ctx.candidates:
            return ctx

        features = self._extract_features(ctx)
        scores = self._predict(features)

        for item, score in zip(ctx.candidates, scores):
            item.score = score

        # 过滤低分
        ctx.candidates = [item for item in ctx.candidates if item.score >= self._threshold]
        sort_by_score(ctx)
        truncate_candidates(ctx, self._max_candidates)

        logger.debug(f"粗排完成", input=len(features), output=len(ctx.candidates))
        return ctx

    def _extract_features(self, ctx: RecContext) -> list[dict]:
        """提取粗排特征。"""
        features = []
        for item in ctx.candidates:
            feat = {**ctx.user_features, **item.features, **ctx.context_features}
            features.append(feat)
        return features

    def _predict(self, features: list[dict]) -> list[float]:
        """模型打分。"""
        if self._model is None:
            import numpy as np
            return np.random.random(len(features)).tolist()

        import numpy as np

        # 将特征转为数组
        feature_arrays = []
        for feat in features:
            arr = [float(v) for v in feat.values() if isinstance(v, (int, float))]
            feature_arrays.append(arr)

        if not feature_arrays:
            return [0.0] * len(features)

        return self._model.predict(np.array(feature_arrays, dtype=np.float32)).tolist()

    def warmup(self) -> None:
        # 模型由 ModelManager 管理，此处可选加载
        pass
