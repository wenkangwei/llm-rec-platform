"""Monitor Agent — 监控分析 Agent"""

from __future__ import annotations

from typing import Any

from llm.agent.base import Agent, AgentResult, AgentTask, Tool
from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.monitor")


class MonitorAgent(Agent):
    """监控分析 Agent：定期分析监控数据，识别异常。"""

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    def available_tools(self) -> list[Tool]:
        return []

    async def run(self, task: AgentTask) -> AgentResult:
        metrics = task.context.get("metrics", {})
        prompt = get_prompt_manager().render(
            "monitor_agent", metrics=_format_metrics(metrics)
        )
        answer = await self._llm.generate(prompt)
        return AgentResult(task_id=task.task_id, answer=answer)

    async def analyze_metrics(self, metrics: dict[str, Any]) -> str:
        """便捷方法：分析监控指标。"""
        task = AgentTask(
            task_id="monitor_analysis",
            description="分析系统监控指标",
            context={"metrics": metrics},
        )
        result = await self.run(task)
        return result.answer


def _format_metrics(metrics: dict[str, Any]) -> str:
    """格式化监控指标。"""
    lines = []
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "暂无监控数据"
