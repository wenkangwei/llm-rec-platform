"""调试诊断意图处理器"""

from __future__ import annotations

from typing import Any

from llm.chat.schemas import Intent
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.handlers.debug")


class DebugHandler:
    """调试诊断意图处理器。

    处理：分析用户123的推荐结果为什么偏少、诊断链路异常等。
    """

    async def handle(self, intent: Intent, context: dict[str, Any]) -> dict[str, Any]:
        user_id = intent.entities.get("user_id", "unknown")
        return {
            "answer": f"正在诊断用户 {user_id} 的推荐情况...",
            "intent": intent.type.value,
            "user_id": user_id,
        }
