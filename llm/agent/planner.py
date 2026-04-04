"""Planner Agent — 策略分析与计划生成"""

from __future__ import annotations

from llm.agent.base import Agent, AgentResult, AgentTask, Step, Tool
from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.planner")


class PlannerAgent(Agent):
    """策略分析 Agent：分析链路状态并生成调整计划。"""

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    def available_tools(self) -> list[Tool]:
        return []

    async def run(self, task: AgentTask) -> AgentResult:
        prompt = get_prompt_manager().render("planner", task=task.description)
        answer = await self._llm.generate(prompt)
        return AgentResult(task_id=task.task_id, answer=answer)
