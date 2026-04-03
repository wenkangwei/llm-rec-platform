"""Planner Agent — 策略分析与计划生成"""

from __future__ import annotations

from llm.agent.base import Agent, AgentResult, AgentTask, Step, Tool
from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.planner")

_PLANNER_PROMPT = """你是一个推荐系统策略分析专家。
用户需求: {task}

请分析当前推荐链路的状态，给出调整建议。

请按以下格式回答:
1. 当前状态分析
2. 建议调整
3. 预期效果

分析:"""


class PlannerAgent(Agent):
    """策略分析 Agent：分析链路状态并生成调整计划。"""

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    def available_tools(self) -> list[Tool]:
        return []

    async def run(self, task: AgentTask) -> AgentResult:
        prompt = _PLANNER_PROMPT.format(task=task.description)
        answer = await self._llm.generate(prompt)
        return AgentResult(task_id=task.task_id, answer=answer)
