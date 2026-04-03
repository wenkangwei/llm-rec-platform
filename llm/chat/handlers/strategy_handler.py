"""策略控制意图处理器"""

from __future__ import annotations

from typing import Any

from llm.chat.schemas import Intent
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.handlers.strategy")


class StrategyHandler:
    """策略控制意图处理器。

    处理：关闭热门召回、调整协同过滤权重、切换排序模型等。
    """

    async def handle(self, intent: Intent, context: dict[str, Any]) -> dict[str, Any]:
        entities = intent.entities
        message = context.get("message", "")

        # 解析操作类型
        action = self._parse_action(message)

        return {
            "answer": f"已识别策略控制意图: {action}。正在通过 Agent 执行...",
            "intent": intent.type.value,
            "parsed_action": action,
            "entities": entities,
        }

    @staticmethod
    def _parse_action(message: str) -> str:
        """从消息中解析操作。"""
        if "关闭" in message or "禁用" in message:
            return "disable"
        elif "启用" in message or "开启" in message:
            return "enable"
        elif "权重" in message or "调" in message:
            return "set_weight"
        elif "切换" in message:
            return "switch"
        return "unknown"
