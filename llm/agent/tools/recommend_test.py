"""推荐测试工具 — 通过 Agent 触发推荐请求并返回格式化结果"""

from __future__ import annotations

import time
from typing import Any

from llm.agent.base import Tool
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.tools.recommend_test")


class RecommendTestTool(Tool):
    """推荐请求测试工具：执行一次推荐请求并返回结果分析。"""

    def __init__(self, pipeline_executor=None):
        self._executor = pipeline_executor

    def name(self) -> str:
        return "recommend_test"

    def description(self) -> str:
        return (
            "执行推荐系统测试请求，返回推荐结果和各阶段性能数据。"
            "参数: user_id(用户ID，默认test_user), "
            "scene(场景: home_feed/follow_feed/community_feed，默认home_feed), "
            "num(推荐数量，默认10)"
        )

    async def execute(self, params: dict[str, Any]) -> Any:
        if not self._executor:
            return {"error": "PipelineExecutor 未初始化，无法执行推荐测试"}

        user_id = params.get("user_id", "test_user")
        scene = params.get("scene", "home_feed")
        num = min(int(params.get("num", 10)), 50)

        try:
            from protocols.schemas.converters import request_to_context, context_to_response
            from protocols.schemas.request import RecRequest

            req = RecRequest(user_id=user_id, scene=scene, num=num)
            ctx = request_to_context(req, request_id="test_req")

            start = time.time()
            ctx = await self._executor.execute(ctx)
            latency_ms = round((time.time() - start) * 1000, 1)

            # 收集结果
            items = []
            for item in ctx.candidates[:num]:
                items.append({
                    "item_id": item.id,
                    "score": round(item.score, 4),
                    "source": item.source,
                })

            stage_metrics = []
            for sm in ctx.stage_metrics:
                stage_metrics.append({
                    "stage": sm.stage_name,
                    "latency_ms": round(sm.latency_ms, 1),
                    "input": sm.input_count,
                    "output": sm.output_count,
                })

            return {
                "items": items,
                "stage_metrics": stage_metrics,
                "total_candidates": len(ctx.candidates),
                "latency_ms": latency_ms,
                "degraded": ctx.degraded,
                "degraded_stages": ctx.degraded_stages,
                "experiment_id": ctx.experiment_id,
                "variant": ctx.variant_name,
            }

        except Exception as e:
            logger.error(f"推荐测试失败: {e}")
            return {"error": str(e)}

    def schema(self) -> dict:
        return {
            "user_id": {"type": "string", "default": "test_user", "description": "测试用户ID"},
            "scene": {
                "type": "string",
                "enum": ["home_feed", "follow_feed", "community_feed"],
                "default": "home_feed",
                "description": "推荐场景",
            },
            "num": {"type": "integer", "default": 10, "maximum": 50, "description": "推荐数量"},
        }
