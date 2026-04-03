"""配置管理意图处理器"""

from __future__ import annotations

from typing import Any

from llm.chat.schemas import Intent
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.handlers.config")


class ConfigHandler:
    """配置管理意图处理器。

    处理：切换精排模型到v2、开启A/B实验、修改参数等。
    """

    async def handle(self, intent: Intent, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "answer": "已识别配置变更意图，正在执行...",
            "intent": intent.type.value,
        }
