"""Critic Agent — 结果评估"""

from __future__ import annotations

from llm.agent.base import Agent, AgentResult, AgentTask
from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.critic")

_CRITIC_PROMPT = """你是一个推荐系统运维审核专家。
用户需求: {task}
执行结果: {result}

请评估执行结果是否满足需求:
1. 是否正确执行了用户意图
2. 是否有潜在风险
3. 是否需要回滚

评估:"""


class CriticAgent(Agent):
    """结果评估 Agent：评估执行结果的质量和风险。"""

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    def available_tools(self) -> list:
        return []

    async def run(self, task: AgentTask) -> AgentResult:
        # 通常 task.context 包含原始需求和执行结果
        result_text = str(task.context.get("result", ""))
        prompt = _CRITIC_PROMPT.format(task=task.description, result=result_text)
        answer = await self._llm.generate(prompt)
        return AgentResult(task_id=task.task_id, answer=answer)
