"""链路控制工具 — 召回通道开关/权重调整"""

from __future__ import annotations

from typing import Any

from llm.agent.base import Tool
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.tools.pipeline")


class PipelineControlTool(Tool):
    """链路控制工具：管理召回通道和排序策略。"""

    def __init__(self, pipeline_state: dict[str, Any] | None = None):
        # pipeline_state 由外部注入，共享引用
        self._state = pipeline_state or {
            "channels": {
                "personalized": {"enabled": True, "weight": 0.30},
                "collaborative": {"enabled": True, "weight": 0.20},
                "social": {"enabled": True, "weight": 0.15},
                "community": {"enabled": True, "weight": 0.10},
                "hot": {"enabled": True, "weight": 0.10},
                "operator": {"enabled": True, "weight": 0.05},
                "cold_start": {"enabled": True, "weight": 0.10},
            }
        }

    def name(self) -> str:
        return "pipeline_control"

    def description(self) -> str:
        return "控制推荐链路：启用/禁用召回通道、调整通道权重、切换排序策略。参数: action(enable/disable/set_weight), channel(通道名), weight(权重)"

    async def execute(self, params: dict[str, Any]) -> Any:
        action = params.get("action", "")
        channel = params.get("channel", "")
        weight = params.get("weight")

        if action == "enable":
            return self._enable_channel(channel)
        elif action == "disable":
            return self._disable_channel(channel)
        elif action == "set_weight":
            return self._set_weight(channel, float(weight or 0.1))
        elif action == "list":
            return self._list_channels()
        else:
            return {"error": f"未知操作: {action}"}

    def _enable_channel(self, channel: str) -> dict:
        if channel in self._state["channels"]:
            self._state["channels"][channel]["enabled"] = True
            logger.info(f"启用召回通道: {channel}")
            return {"success": True, "channel": channel, "enabled": True}
        return {"error": f"通道不存在: {channel}"}

    def _disable_channel(self, channel: str) -> dict:
        if channel in self._state["channels"]:
            self._state["channels"][channel]["enabled"] = False
            logger.info(f"禁用召回通道: {channel}")
            return {"success": True, "channel": channel, "enabled": False}
        return {"error": f"通道不存在: {channel}"}

    def _set_weight(self, channel: str, weight: float) -> dict:
        if channel in self._state["channels"]:
            self._state["channels"][channel]["weight"] = weight
            logger.info(f"调整通道权重: {channel}", weight=weight)
            return {"success": True, "channel": channel, "weight": weight}
        return {"error": f"通道不存在: {channel}"}

    def _list_channels(self) -> dict:
        return {"channels": self._state["channels"]}

    def schema(self) -> dict:
        return {
            "action": {"type": "string", "enum": ["enable", "disable", "set_weight", "list"]},
            "channel": {"type": "string"},
            "weight": {"type": "number"},
        }
