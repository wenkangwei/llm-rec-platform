"""召回合并器 — 多路召回结果去重合并"""

from __future__ import annotations

import importlib

from pipeline.base import PipelineStage
from pipeline.context import dedup_items, sort_by_score
from protocols.schemas.context import Item, RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("recall.merger")


class RecallMerger(PipelineStage):
    """多路召回合并器。

    顺序执行所有启用的召回通道，合并去重后输出统一候选集。
    生产环境可升级为 asyncio.gather 并行执行。
    """

    def __init__(self):
        self._channels: list[PipelineStage] = []
        self._load_channels_from_config()

    def name(self) -> str:
        return "recall"

    def _load_channels_from_config(self) -> None:
        """从配置文件自动加载召回通道。"""
        try:
            from configs.settings import get_settings
            settings = get_settings()
            recall_config = settings.raw.get("pipeline", {}).get("recall", {})
            # recall 可能是 channels dict 本身，或包含 channels 子键
            channels_config = recall_config.get("channels", recall_config)

            for ch_name in sorted(channels_config.keys()):
                ch_cfg = channels_config[ch_name]
                if not ch_cfg.get("enabled", True):
                    continue
                class_path = ch_cfg.get("class", "")
                if not class_path:
                    continue
                try:
                    module_path, class_name = class_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    ch_cls = getattr(module, class_name)
                    channel = ch_cls()
                    self._channels.append(channel)
                    logger.info(f"自动加载召回通道: {ch_name}", class_path=class_path)
                except Exception as e:
                    logger.error(f"加载召回通道失败: {ch_name}", error=str(e))
        except Exception as e:
            logger.warning(f"召回通道配置加载失败", error=str(e))

    def register_channel(self, channel: PipelineStage) -> None:
        """手动注册召回通道。"""
        self._channels.append(channel)
        logger.info(f"注册召回通道: {channel.name()}")

    async def process(self, ctx: RecContext) -> RecContext:
        """并行执行所有召回通道并合并结果。"""
        import asyncio

        async def _run_channel(channel: PipelineStage) -> list[Item]:
            """运行单个召回通道。"""
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
                if hasattr(result, "__await__"):
                    result = await result
                items = result.candidates
                logger.debug(f"通道 {channel.name()} 召回 {len(items)} 条")
                return items
            except Exception as e:
                logger.error(f"召回通道异常: {channel.name()}", error=str(e))
                return []

        # 并行执行所有通道
        results = await asyncio.gather(*[_run_channel(ch) for ch in self._channels])

        all_items: list[Item] = []
        for items in results:
            all_items.extend(items)

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
            except Exception as e:
                logger.debug(f"通道关闭异常", error=str(e))
