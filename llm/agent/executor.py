"""Agent 执行器 — LangChain ReAct Agent 实现"""

from __future__ import annotations

from typing import Any

from llm.agent.base import Agent, AgentResult, AgentTask, Step, Tool
from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.executor")


class ReActAgent(Agent):
    """ReAct Agent：Reasoning + Acting 交替执行。

    使用 LangChain 的 ReAct 模式实现。
    """

    def __init__(self, llm: LLMBackend, tools: list[Tool], max_iterations: int = 5):
        self._llm = llm
        self._tools = {t.name(): t for t in tools}
        self._max_iterations = max_iterations
        self._langchain_agent = None

    def available_tools(self) -> list[Tool]:
        return list(self._tools.values())

    async def run(self, task: AgentTask) -> AgentResult:
        """执行任务：循环 Thought → Action → Observation。"""
        steps: list[Step] = []
        prompt = self._build_initial_prompt(task)
        answer = ""

        for i in range(self._max_iterations):
            # Thought: LLM 生成思考
            response = await self._llm.generate(prompt)
            logger.debug(f"Agent 迭代 {i + 1}", response=response[:200])

            # 解析 Action
            action = self._parse_action(response)
            if action is None:
                # 没有更多 action，提取最终答案
                answer = self._extract_answer(response)
                break

            # Action: 执行工具
            tool_name = action["tool"]
            params = action["params"]
            step = Step(tool_name=tool_name, params=params)

            tool = self._tools.get(tool_name)
            if tool:
                try:
                    result = await tool.execute(params)
                    step.result = result
                    step.status = "success"
                    observation = f"工具 {tool_name} 返回: {str(result)[:500]}"
                except Exception as e:
                    step.result = str(e)
                    step.status = "failed"
                    observation = f"工具 {tool_name} 执行失败: {e}"
            else:
                step.status = "failed"
                observation = f"工具 {tool_name} 不存在"

            steps.append(step)
            prompt += f"\nObservation: {observation}\nThought:"

        return AgentResult(task_id=task.task_id, answer=answer, steps=steps, success=True)

    def _build_initial_prompt(self, task: AgentTask) -> str:
        """构建初始 prompt。"""
        tools_desc = "\n".join(
            f"- {t.name()}: {t.description()}"
            for t in self._tools.values()
        )
        return (
            f"你是一个推荐系统运维助手。用户需求: {task.description}\n"
            f"可用工具:\n{tools_desc}\n"
            f"请使用 Thought/Action/Observation 格式回答。\n"
            f"Thought:"
        )

    def _parse_action(self, response: str) -> dict | None:
        """解析 LLM 输出中的 Action。"""
        import re
        match = re.search(r"Action:\s*(\w+)\((.*)\)", response, re.IGNORECASE)
        if match:
            return {"tool": match.group(1), "params": {"raw": match.group(2)}}
        return None

    def _extract_answer(self, response: str) -> str:
        """提取最终答案。"""
        import re
        match = re.search(r"Answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()
