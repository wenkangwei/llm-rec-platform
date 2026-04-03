"""策略重排 — 多样性/去重/Fatigue 控制"""

from __future__ import annotations

from collections import Counter

from pipeline.base import PipelineStage
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("ranking.rerank")


class ReRankStage(PipelineStage):
    """策略重排阶段：业务规则 + 多样性 + 疲劳控制。"""

    def __init__(
        self,
        same_author_max: int = 2,
        same_tag_max: int = 3,
        mmr_lambda: float = 0.5,
        recent_expose_window: int = 100,
        max_repeat: int = 2,
        new_content_weight: float = 1.2,
        followed_author_weight: float = 1.1,
    ):
        self._same_author_max = same_author_max
        self._same_tag_max = same_tag_max
        self._mmr_lambda = mmr_lambda
        self._expose_window = recent_expose_window
        self._max_repeat = max_repeat
        self._new_weight = new_content_weight
        self._followed_weight = followed_author_weight

    def name(self) -> str:
        return "rerank"

    def process(self, ctx: RecContext) -> RecContext:
        if not ctx.candidates:
            return ctx

        # 1. 业务加权
        self._apply_boost(ctx)

        # 2. 疲劳控制（过滤最近已曝光内容）
        self._fatigue_filter(ctx)

        # 3. 多样性打散
        self._diversity_rerank(ctx)

        # 4. 去重
        seen = set()
        ctx.candidates = [item for item in ctx.candidates if not (item.id in seen or seen.add(item.id))]

        logger.debug(f"重排完成", output=len(ctx.candidates))
        return ctx

    def _apply_boost(self, ctx: RecContext) -> None:
        """业务加权。"""
        following_ids = set(ctx.user_features.get("following_ids", []))
        for item in ctx.candidates:
            author_id = item.features.get("author_id", "")
            is_new = item.features.get("is_new", False)

            if author_id in following_ids:
                item.score *= self._followed_weight
            if is_new:
                item.score *= self._new_weight

    def _fatigue_filter(self, ctx: RecContext) -> None:
        """疲劳控制：过滤最近重复曝光的内容。"""
        recent_exposed = set(ctx.user_features.get("recent_exposed_items", []))
        if not recent_exposed:
            return

        ctx.candidates = [
            item for item in ctx.candidates
            if item.id not in recent_exposed
        ]

    def _diversity_rerank(self, ctx: RecContext) -> None:
        """多样性打散：MMR 策略。"""
        if len(ctx.candidates) <= 1:
            return

        result = []
        remaining = list(ctx.candidates)
        author_count: Counter = Counter()
        tag_count: Counter = Counter()

        while remaining and len(result) < len(ctx.candidates):
            best_idx = 0
            best_score = -float("inf")

            for i, item in enumerate(remaining):
                # 检查同作者/同标签限制
                author = item.features.get("author_id", "")
                tags = item.features.get("tags", [])

                penalty = 0.0
                if author and author_count[author] >= self._same_author_max:
                    penalty -= 1.0
                for tag in tags:
                    if tag_count[tag] >= self._same_tag_max:
                        penalty -= 0.3

                # MMR: lambda * relevance + (1-lambda) * diversity
                relevance = item.score
                diversity = penalty
                mmr_score = self._mmr_lambda * relevance + (1 - self._mmr_lambda) * diversity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected = remaining.pop(best_idx)
            result.append(selected)

            author = selected.features.get("author_id", "")
            if author:
                author_count[author] += 1
            for tag in selected.features.get("tags", []):
                tag_count[tag] += 1

        ctx.candidates = result
