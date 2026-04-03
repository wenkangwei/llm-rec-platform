"""链路执行器 — 配置驱动，动态加载 PipelineStage"""

from __future__ import annotations

import importlib
import time
from typing import Any

from pipeline.base import PipelineStage
from pipeline.context import add_stage_metrics
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("pipeline.executor")


class PipelineExecutor:
    """推荐链路执行器。

    从配置文件加载 stage 列表，按顺序执行。
    每个阶段独立计时，单阶段失败不影响整体请求。
    """

    def __init__(self):
        self._stages: list[PipelineStage] = []

    def register(self, stage: PipelineStage) -> None:
        """注册一个链路阶段。"""
        self._stages.append(stage)
        logger.info(f"注册链路阶段: {stage.name()}")

    def load_from_config(self, stage_configs: list[dict[str, Any]]) -> None:
        """从配置动态加载所有阶段。

        stage_configs 格式:
        [
            {"name": "recall", "class": "pipeline.recall.merger.RecallMerger", "timeout_ms": 50},
            ...
        ]
        """
        for cfg in stage_configs:
            stage = self._load_stage(cfg)
            if stage:
                self.register(stage)

    @staticmethod
    def _load_stage(cfg: dict[str, Any]) -> PipelineStage | None:
        """动态加载一个 PipelineStage 类并实例化。"""
        class_path = cfg.get("class") or cfg.get("class_path", "")
        if not class_path:
            logger.warning(f"阶段缺少 class 配置: {cfg.get('name')}")
            return None

        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            stage_cls = getattr(module, class_name)
            return stage_cls()
        except Exception as e:
            logger.error(f"加载阶段失败: {class_path}", error=str(e))
            return None

    async def execute(self, ctx: RecContext) -> RecContext:
        """执行完整链路。"""
        for stage in self._stages:
            stage_name = stage.name()
            start = time.perf_counter()
            input_count = len(ctx.candidates)

            try:
                ctx = await self._run_stage(stage, ctx)
                elapsed_ms = (time.perf_counter() - start) * 1000
                output_count = len(ctx.candidates)
                add_stage_metrics(ctx, stage_name, elapsed_ms, input_count, output_count)
                logger.debug(
                    f"阶段完成: {stage_name}",
                    latency_ms=f"{elapsed_ms:.1f}",
                    input=input_count,
                    output=output_count,
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                add_stage_metrics(ctx, stage_name, elapsed_ms, input_count, 0, {"error": str(e)})
                logger.error(f"阶段异常: {stage_name}", error=str(e))
                # 标记降级
                ctx.degraded = True
                ctx.degraded_stages.append(stage_name)

        return ctx

    @staticmethod
    async def _run_stage(stage: PipelineStage, ctx: RecContext) -> RecContext:
        """执行单个阶段，支持同步和异步 process 方法。"""
        result = stage.process(ctx)
        # 如果 process 返回协程则 await
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def warmup_all(self) -> None:
        """预热所有阶段。"""
        for stage in self._stages:
            try:
                stage.warmup()
                logger.info(f"阶段预热完成: {stage.name()}")
            except Exception as e:
                logger.error(f"阶段预热失败: {stage.name()}", error=str(e))

    async def shutdown_all(self) -> None:
        """关闭所有阶段。"""
        for stage in reversed(self._stages):
            try:
                stage.shutdown()
            except Exception as e:
                logger.error(f"阶段关闭失败: {stage.name()}", error=str(e))

    def health_check(self) -> dict[str, bool]:
        """检查所有阶段健康状态。"""
        return {stage.name(): stage.health_check() for stage in self._stages}
