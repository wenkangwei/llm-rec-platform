"""Critic Agent — 结果评估"""

from __future__ import annotations

from llm.agent.base import Agent, AgentResult, AgentTask
from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.critic")


class CriticAgent(Agent):
    """结果评估 Agent：评估执行结果的质量和风险。"""

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    def available_tools(self) -> list:
        return []

    async def run(self, task: AgentTask) -> AgentResult:
        # 通常 task.context 包含原始需求和执行结果
        result_text = str(task.context.get("result", ""))
        prompt = get_prompt_manager().render(
            "critic", task=task.description, result=result_text
        )
        answer = await self._llm.generate(prompt)
        return AgentResult(task_id=task.task_id, answer=answer)
