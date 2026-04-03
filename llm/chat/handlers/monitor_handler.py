"""监控查询意图处理器"""

from __future__ import annotations

from typing import Any

from llm.chat.schemas import Intent
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.handlers.monitor")


class MonitorHandler:
    """监控查询意图处理器。

    处理：P99延迟多少、召回覆盖率正常吗、QPS多少等。
    """

    async def handle(self, intent: Intent, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "answer": "正在查询监控指标...",
            "intent": intent.type.value,
            "query_type": self._detect_metric(context.get("message", "")),
        }

    @staticmethod
    def _detect_metric(message: str) -> str:
        if "延迟" in message or "P99" in message:
            return "latency"
        elif "QPS" in message or "qps" in message:
            return "qps"
        elif "覆盖率" in message or "召回" in message:
            return "recall_coverage"
        return "all"
