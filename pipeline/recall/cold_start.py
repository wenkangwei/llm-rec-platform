"""冷启动召回 — 新用户/新内容"""

from __future__ import annotations

import random

from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.cold_start")


class ColdStartRecall(PipelineStage):
    """冷启动召回：新用户探索 + 新内容扶持。

    策略：
    - 新用户：全局热门 + 随机探索
    - 新内容：LLM 内容模拟 + 探索流量
    """

    def __init__(self, top_k: int = 200, explore_ratio: float = 0.1):
        self._top_k = top_k
        self._explore_ratio = explore_ratio
        self._new_items: list[tuple[str, float]] = []

    def name(self) -> str:
        return "cold_start"

    def process(self, ctx: RecContext) -> RecContext:
        is_cold = ctx.user_features.get("cold_start", False)

        if is_cold:
            # 新用户：热门 + 随机探索
            self._recall_for_new_user(ctx)
        else:
            # 老用户：新内容扶持
            self._recall_new_items(ctx)

        return ctx

    def _recall_for_new_user(self, ctx: RecContext) -> None:
        """新用户冷启动召回。"""
        # 热门内容兜底
        count = int(self._top_k * (1 - self._explore_ratio))
        for item_id, score in self._get_hot_items()[:count]:
            ctx.candidates.append(Item(id=item_id, score=score, source="cold_start"))

        # 随机探索
        explore_count = self._top_k - count
        for item_id, score in self._get_explore_items(explore_count):
            ctx.candidates.append(Item(
                id=item_id,
                score=score,
                source="cold_start_explore",
            ))

    def _recall_new_items(self, ctx: RecContext) -> None:
        """新内容扶持召回。"""
        for item_id, score in self._new_items[:self._top_k]:
            ctx.candidates.append(Item(
                id=item_id,
                score=score * 1.2,  # 新内容加权
                source="cold_start_new",
            ))

    def _get_hot_items(self) -> list[tuple[str, float]]:
        """获取热门物品。"""
        # TODO: 从 Redis 获取
        return []

    def _get_explore_items(self, count: int) -> list[tuple[str, float]]:
        """随机探索物品。"""
        # TODO: 从物品池随机采样
        return []

    def update_new_items(self, items: list[tuple[str, float]]) -> None:
        """更新新内容列表。"""
        self._new_items = items
