"""LangGraph 对话路由 — 意图识别 → 工具调用 → 结果反馈"""

from __future__ import annotations

from typing import Any

from llm.chat.schemas import Intent, IntentType
from llm.chat.handlers.strategy_handler import StrategyHandler
from llm.chat.handlers.monitor_handler import MonitorHandler
from llm.chat.handlers.debug_handler import DebugHandler
from llm.chat.handlers.config_handler import ConfigHandler
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.router")


class ChatRouter:
    """对话路由：根据意图分发到对应处理器。

    当前使用关键词路由。后续可升级为 LangGraph StateGraph。
    """

    def __init__(self):
        self._handlers: dict[IntentType, Any] = {
            IntentType.STRATEGY: StrategyHandler(),
            IntentType.MONITOR: MonitorHandler(),
            IntentType.DEBUG: DebugHandler(),
            IntentType.CONFIG: ConfigHandler(),
        }

    async def route(self, intent: Intent, context: dict[str, Any]) -> dict[str, Any]:
        """路由到对应处理器。"""
        handler = self._handlers.get(intent.type)
        if handler:
            return await handler.handle(intent, context)
        return {"answer": "抱歉，我不太理解您的意图，请重新描述。", "actions": []}
