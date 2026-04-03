"""Agent / Tool 抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTask:
    """Agent 任务。"""
    task_id: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """执行步骤。"""
    tool_name: str
    params: dict[str, Any]
    result: Any = None
    status: str = "pending"  # pending / success / failed


@dataclass
class AgentResult:
    """Agent 执行结果。"""
    task_id: str
    answer: str
    steps: list[Step] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class Tool(ABC):
    """Agent 工具抽象接口。"""

    @abstractmethod
    def name(self) -> str:
        """工具名称。"""

    @abstractmethod
    def description(self) -> str:
        """工具描述（给 LLM 看）。"""

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> Any:
        """执行工具。"""

    def schema(self) -> dict[str, Any]:
        """参数 schema。"""
        return {}


class Agent(ABC):
    """Agent 抽象接口。"""

    @abstractmethod
    async def run(self, task: AgentTask) -> AgentResult:
        """执行任务。"""

    @abstractmethod
    def available_tools(self) -> list[Tool]:
        """可用工具列表。"""

    def plan(self, task: AgentTask) -> list[Step]:
        """规划执行步骤。默认空实现。"""
        return []

    def reflect(self, result: AgentResult) -> str | None:
        """反思执行结果。默认空实现。"""
        return None
