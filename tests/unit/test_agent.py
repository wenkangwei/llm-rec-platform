"""Agent 模块单元测试 — base/planner/executor/critic/tools"""

from __future__ import annotations

import asyncio

import pytest

from llm.agent.base import Agent, AgentResult, AgentTask, Step, Tool
from llm.agent.planner import PlannerAgent
from llm.agent.critic import CriticAgent
from llm.agent.executor import ReActAgent
from llm.agent.tools.pipeline_control import PipelineControlTool
from llm.agent.tools.monitor_query import MonitorQueryTool
from llm.agent.tools.config_update import ConfigUpdateTool
from llm.backends.mock_backend import MockBackend


# ---------- base dataclasses ----------

class TestAgentTask:
    def test_defaults(self):
        task = AgentTask(task_id="t1", description="test")
        assert task.context == {}

    def test_with_context(self):
        task = AgentTask(task_id="t1", description="test", context={"k": "v"})
        assert task.context["k"] == "v"


class TestStep:
    def test_defaults(self):
        step = Step(tool_name="tool1", params={"a": 1})
        assert step.result is None
        assert step.status == "pending"

    def test_with_result(self):
        step = Step(tool_name="tool1", params={}, result="ok", status="success")
        assert step.status == "success"


class TestAgentResult:
    def test_defaults(self):
        r = AgentResult(task_id="t1", answer="done")
        assert r.steps == []
        assert r.success is True
        assert r.error is None

    def test_error_result(self):
        r = AgentResult(task_id="t1", answer="", success=False, error="boom")
        assert r.error == "boom"


# ---------- PlannerAgent ----------

class TestPlannerAgent:
    @pytest.fixture
    def planner(self):
        return PlannerAgent(MockBackend())

    def test_available_tools(self, planner):
        assert planner.available_tools() == []

    @pytest.mark.asyncio
    async def test_run(self, planner):
        task = AgentTask(task_id="p1", description="分析召回链路")
        result = await planner.run(task)
        assert result.task_id == "p1"
        assert "[Mock Response]" in result.answer

    def test_plan_default(self, planner):
        task = AgentTask(task_id="p1", description="test")
        assert planner.plan(task) == []

    def test_reflect_default(self, planner):
        r = AgentResult(task_id="p1", answer="ok")
        assert planner.reflect(r) is None


# ---------- CriticAgent ----------

class TestCriticAgent:
    @pytest.fixture
    def critic(self):
        return CriticAgent(MockBackend())

    def test_available_tools(self, critic):
        assert critic.available_tools() == []

    @pytest.mark.asyncio
    async def test_run(self, critic):
        task = AgentTask(
            task_id="c1",
            description="检查执行结果",
            context={"result": "通道已关闭"},
        )
        result = await critic.run(task)
        assert result.task_id == "c1"
        assert result.answer  # non-empty


# ---------- ReActAgent ----------

class _DummyTool(Tool):
    def name(self) -> str:
        return "dummy_tool"

    def description(self) -> str:
        return "A dummy tool for testing"

    async def execute(self, params: dict) -> str:
        return f"executed with {params}"


class _FailTool(Tool):
    def name(self) -> str:
        return "fail_tool"

    def description(self) -> str:
        return "Always fails"

    async def execute(self, params: dict) -> str:
        raise RuntimeError("tool failed")


class TestReActAgent:
    @pytest.fixture
    def agent(self):
        tools = [_DummyTool(), _FailTool()]
        return ReActAgent(MockBackend(), tools, max_iterations=3)

    def test_available_tools(self, agent):
        names = [t.name() for t in agent.available_tools()]
        assert "dummy_tool" in names
        assert "fail_tool" in names

    @pytest.mark.asyncio
    async def test_run_returns_result(self, agent):
        task = AgentTask(task_id="r1", description="test task")
        result = await agent.run(task)
        assert result.task_id == "r1"
        assert isinstance(result.steps, list)
        assert result.success is True

    def test_parse_action(self, agent):
        action = agent._parse_action("some text\nAction: dummy_tool(x=1)\nmore")
        assert action is not None
        assert action["tool"] == "dummy_tool"

    def test_parse_action_no_match(self, agent):
        assert agent._parse_action("just plain text") is None

    def test_extract_answer(self, agent):
        text = "some reasoning\nAnswer: The result is 42"
        assert agent._extract_answer(text) == "The result is 42"

    def test_extract_answer_no_prefix(self, agent):
        text = "just plain response"
        assert agent._extract_answer(text) == "just plain response"


# ---------- PipelineControlTool ----------

class TestPipelineControlTool:
    @pytest.fixture
    def tool(self):
        return PipelineControlTool()

    def test_name_and_description(self, tool):
        assert tool.name() == "pipeline_control"
        assert tool.description()

    @pytest.mark.asyncio
    async def test_enable_channel(self, tool):
        result = await tool.execute({"action": "enable", "channel": "hot"})
        assert result["success"] is True
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_disable_channel(self, tool):
        result = await tool.execute({"action": "disable", "channel": "hot"})
        assert result["success"] is True
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_set_weight(self, tool):
        result = await tool.execute({"action": "set_weight", "channel": "collaborative", "weight": 0.5})
        assert result["success"] is True
        assert result["weight"] == 0.5

    @pytest.mark.asyncio
    async def test_list_channels(self, tool):
        result = await tool.execute({"action": "list"})
        assert "channels" in result
        assert "hot" in result["channels"]

    @pytest.mark.asyncio
    async def test_unknown_channel(self, tool):
        result = await tool.execute({"action": "enable", "channel": "nonexistent"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute({"action": "explode", "channel": "hot"})
        assert "error" in result

    def test_schema(self, tool):
        schema = tool.schema()
        assert "action" in schema
        assert "channel" in schema


# ---------- MonitorQueryTool ----------

class TestMonitorQueryTool:
    @pytest.fixture
    def tool(self):
        return MonitorQueryTool(metrics_store={
            "latency_p99_ms": 120,
            "qps": 600,
            "recall_coverage": 0.95,
        })

    def test_name_and_description(self, tool):
        assert tool.name() == "monitor_query"
        assert tool.description()

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, tool):
        result = await tool.execute({"metric": "all"})
        assert result["latency_p99_ms"] == 120
        assert result["qps"] == 600
        assert result["recall_coverage"] == 0.95
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_latency(self, tool):
        result = await tool.execute({"metric": "latency"})
        assert result["p99_ms"] == 120

    @pytest.mark.asyncio
    async def test_get_qps(self, tool):
        result = await tool.execute({"metric": "qps"})
        assert result["current"] == 600

    @pytest.mark.asyncio
    async def test_get_recall_coverage(self, tool):
        result = await tool.execute({"metric": "recall_coverage"})
        assert result["overall"] == 0.95

    @pytest.mark.asyncio
    async def test_unknown_metric(self, tool):
        result = await tool.execute({"metric": "invalid"})
        # 未知 metric 兜底返回全部指标
        assert "qps" in result or "error" in result

    @pytest.mark.asyncio
    async def test_default_metrics(self):
        tool = MonitorQueryTool()
        result = await tool.execute({"metric": "all"})
        assert result["latency_p99_ms"] == 150  # default


# ---------- ConfigUpdateTool ----------

class TestConfigUpdateTool:
    @pytest.fixture
    def tool(self):
        return ConfigUpdateTool(config_state={
            "models": {"rank": {"version": "v1", "dim": 64}},
        })

    def test_name_and_description(self, tool):
        assert tool.name() == "config_update"
        assert tool.description()

    @pytest.mark.asyncio
    async def test_update_existing_key(self, tool):
        result = await tool.execute({"key": "models.rank.version", "value": "v2"})
        assert result["success"] is True
        assert result["old_value"] == "v1"
        assert result["new_value"] == "v2"

    @pytest.mark.asyncio
    async def test_update_new_key(self, tool):
        result = await tool.execute({"key": "models.rank.lr", "value": 0.001})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_missing_key(self, tool):
        result = await tool.execute({"value": "x"})
        assert "error" in result

    def test_schema(self, tool):
        schema = tool.schema()
        assert "key" in schema
        assert "value" in schema
