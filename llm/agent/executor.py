"""Agent 执行器 — LangChain ReAct Agent 实现"""

from __future__ import annotations

from typing import Any

from llm.agent.base import Agent, AgentResult, AgentTask, Step, Tool
from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
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

        # 如果有 steps 但没有最终 answer，构造友好回复
        if not answer and steps:
            # 只取最后一个成功的工具结果（避免重复）
            last_success = None
            for s in reversed(steps):
                if s.status == "success" and s.result:
                    last_success = s
                    break

            if last_success and isinstance(last_success.result, dict):
                import json
                # 格式化为可读文本
                lines = []
                for k, v in last_success.result.items():
                    if isinstance(v, dict):
                        lines.append(f"- {k}:")
                        for sk, sv in v.items():
                            lines.append(f"  - {sk}: {sv}")
                    else:
                        lines.append(f"- {k}: {v}")
                answer = "\n".join(lines)
            elif last_success:
                answer = str(last_success.result)
            else:
                answer = "未能获取到有效结果。"

        return AgentResult(task_id=task.task_id, answer=answer, steps=steps, success=True)

    def _build_initial_prompt(self, task: AgentTask) -> str:
        """构建初始 prompt。"""
        tools_desc = "\n".join(
            f"- {t.name()}: {t.description()}"
            for t in self._tools.values()
        )
        return get_prompt_manager().render(
            "executor", user_request=task.description, tools=tools_desc
        )

    def _parse_action(self, response: str) -> dict | None:
        """解析 LLM 输出中的 Action。

        支持两种格式：
        1. Action: tool_name\nAction Input: {"key": "val"}
        2. Action: tool_name({"key": "val"})
        """
        import json
        import re

        # 格式 1: Action + Action Input 两行
        action_match = re.search(r"Action:\s*(\w+)", response, re.IGNORECASE)
        if action_match:
            tool_name = action_match.group(1)
            # 检查是否有 Action Input 行
            input_match = re.search(
                r"Action\s*Input:\s*(\{[^}]*\})", response, re.IGNORECASE
            )
            if input_match:
                try:
                    params = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    params = {"raw": input_match.group(1)}
            else:
                # 格式 2: Action: tool_name(params)
                paren_match = re.search(
                    r"Action:\s*\w+\((.*)\)", response, re.IGNORECASE
                )
                if paren_match:
                    try:
                        params = json.loads(paren_match.group(1))
                    except json.JSONDecodeError:
                        params = {"raw": paren_match.group(1)}
                else:
                    params = {}

            # 过滤掉非工具名（如"使用"、"调用"等中文）
            if tool_name in self._tools:
                return {"tool": tool_name, "params": params}
            # 尝试在 response 中找已知工具名
            for name in self._tools:
                if name.lower() in response.lower():
                    return {"tool": name, "params": params}

        return None

    def _extract_answer(self, response: str) -> str:
        """提取最终答案。"""
        import re
        match = re.search(r"Answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()
