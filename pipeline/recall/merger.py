"""召回合并器 — 多路召回结果去重合并"""

from __future__ import annotations

from pipeline.base import PipelineStage
from pipeline.context import dedup_items, sort_by_score, truncate_candidates
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.merger")


class RecallMerger(PipelineStage):
    """多路召回合并器。

    并行执行所有启用的召回通道，合并去重后输出统一候选集。
    """

    def __init__(self):
        self._channels: list[PipelineStage] = []

    def name(self) -> str:
        return "recall"

    def register_channel(self, channel: PipelineStage) -> None:
        """注册召回通道。"""
        self._channels.append(channel)
        logger.info(f"注册召回通道: {channel.name()}")

    def process(self, ctx: RecContext) -> RecContext:
        """执行所有召回通道并合并结果。"""
        all_items: list[Item] = []

        for channel in self._channels:
            try:
                channel_ctx = RecContext(
                    request_id=ctx.request_id,
                    user_id=ctx.user_id,
                    scene=ctx.scene,
                    candidates=[],
                    user_features=ctx.user_features,
                    context_features=ctx.context_features,
                    query=ctx.query,
                )
                result = channel.process(channel_ctx)
                items = result.candidates
                all_items.extend(items)
                logger.debug(f"通道 {channel.name()} 召回 {len(items)} 条")
            except Exception as e:
                logger.error(f"召回通道异常: {channel.name()}", error=str(e))
                # 单通道失败不阻塞

        ctx.candidates = all_items
        dedup_items(ctx)
        sort_by_score(ctx)

        # 记录召回合并统计
        source_stats = {}
        for item in ctx.candidates:
            source_stats[item.source] = source_stats.get(item.source, 0) + 1
        ctx.extras["recall_sources"] = source_stats

        logger.info(
            f"召回合并完成",
            total=len(all_items),
            after_dedup=len(ctx.candidates),
            sources=source_stats,
        )
        return ctx

    def warmup(self) -> None:
        for ch in self._channels:
            try:
                ch.warmup()
            except Exception as e:
                logger.error(f"通道预热失败: {ch.name()}", error=str(e))

    def health_check(self) -> bool:
        return all(ch.health_check() for ch in self._channels) if self._channels else True

    def shutdown(self) -> None:
        for ch in self._channels:
            try:
                ch.shutdown()
            except Exception:
                pass
