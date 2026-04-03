"""llm 扩展模块测试 — chat handlers / router / monitor_agent / tasks / prompt"""

from __future__ import annotations

import pytest

from llm.backends.mock_backend import MockBackend
from llm.chat.handlers.strategy_handler import StrategyHandler
from llm.chat.handlers.monitor_handler import MonitorHandler
from llm.chat.handlers.debug_handler import DebugHandler
from llm.chat.handlers.config_handler import ConfigHandler
from llm.chat.router import ChatRouter
from llm.chat.schemas import Intent, IntentType
from llm.agent.monitor_agent import MonitorAgent, _format_metrics
from llm.tasks.content_gen import ContentGenerator
from llm.tasks.embedder import Embedder
from llm.tasks.rerank_summary import RerankSummary
from llm.tasks.semantic_search import SemanticSearch
from llm.prompt.manager import PromptManager


# ========== Chat Handlers ==========

class TestStrategyHandler:
    @pytest.fixture
    def handler(self):
        return StrategyHandler()

    @pytest.mark.asyncio
    async def test_handle(self, handler):
        intent = Intent(type=IntentType.STRATEGY, confidence=1.0, entities={"channel": "hot"})
        result = await handler.handle(intent, {"message": "关闭热门召回"})
        assert "策略控制意图" in result["answer"]
        assert result["parsed_action"] == "disable"

    def test_parse_action_disable(self, handler):
        assert handler._parse_action("关闭热门召回") == "disable"
        assert handler._parse_action("禁用协同过滤") == "disable"

    def test_parse_action_enable(self, handler):
        assert handler._parse_action("启用热门召回") == "enable"
        assert handler._parse_action("开启新通道") == "enable"

    def test_parse_action_set_weight(self, handler):
        assert handler._parse_action("权重调到0.5") == "set_weight"

    def test_parse_action_switch(self, handler):
        assert handler._parse_action("切换精排模型") == "switch"

    def test_parse_action_unknown(self, handler):
        assert handler._parse_action("随便说点什么") == "unknown"


class TestMonitorHandler:
    @pytest.fixture
    def handler(self):
        return MonitorHandler()

    @pytest.mark.asyncio
    async def test_handle(self, handler):
        intent = Intent(type=IntentType.MONITOR, confidence=1.0)
        result = await handler.handle(intent, {"message": "P99延迟多少"})
        assert "监控指标" in result["answer"]
        assert result["query_type"] == "latency"

    def test_detect_metric_latency(self, handler):
        assert handler._detect_metric("延迟正常吗") == "latency"
        assert handler._detect_metric("P99多少") == "latency"

    def test_detect_metric_qps(self, handler):
        assert handler._detect_metric("QPS是多少") == "qps"

    def test_detect_metric_recall(self, handler):
        assert handler._detect_metric("召回覆盖率") == "recall_coverage"

    def test_detect_metric_all(self, handler):
        assert handler._detect_metric("整体监控") == "all"


class TestDebugHandler:
    @pytest.fixture
    def handler(self):
        return DebugHandler()

    @pytest.mark.asyncio
    async def test_handle(self, handler):
        intent = Intent(type=IntentType.DEBUG, confidence=1.0, entities={"user_id": "123"})
        result = await handler.handle(intent, {})
        assert "123" in result["answer"]
        assert result["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_handle_no_user(self, handler):
        intent = Intent(type=IntentType.DEBUG, confidence=1.0, entities={})
        result = await handler.handle(intent, {})
        assert result["user_id"] == "unknown"


class TestConfigHandler:
    @pytest.fixture
    def handler(self):
        return ConfigHandler()

    @pytest.mark.asyncio
    async def test_handle(self, handler):
        intent = Intent(type=IntentType.CONFIG, confidence=1.0)
        result = await handler.handle(intent, {})
        assert "配置变更" in result["answer"]


class TestChatRouter:
    @pytest.fixture
    def router(self):
        return ChatRouter()

    @pytest.mark.asyncio
    async def test_route_strategy(self, router):
        intent = Intent(type=IntentType.STRATEGY, confidence=1.0)
        result = await router.route(intent, {"message": "关闭热门召回"})
        assert "策略控制意图" in result["answer"]

    @pytest.mark.asyncio
    async def test_route_monitor(self, router):
        intent = Intent(type=IntentType.MONITOR, confidence=1.0)
        result = await router.route(intent, {"message": "P99"})
        assert "监控指标" in result["answer"]

    @pytest.mark.asyncio
    async def test_route_debug(self, router):
        intent = Intent(type=IntentType.DEBUG, confidence=1.0, entities={"user_id": "u1"})
        result = await router.route(intent, {})
        assert "诊断" in result["answer"]

    @pytest.mark.asyncio
    async def test_route_config(self, router):
        intent = Intent(type=IntentType.CONFIG, confidence=1.0)
        result = await router.route(intent, {})
        assert "配置变更" in result["answer"]

    @pytest.mark.asyncio
    async def test_route_unknown(self, router):
        intent = Intent(type=IntentType.UNKNOWN, confidence=0.0)
        result = await router.route(intent, {})
        assert "不太理解" in result["answer"]


# ========== MonitorAgent ==========

class TestMonitorAgent:
    @pytest.fixture
    def agent(self):
        return MonitorAgent(MockBackend())

    def test_available_tools(self, agent):
        assert agent.available_tools() == []

    @pytest.mark.asyncio
    async def test_run(self, agent):
        from llm.agent.base import AgentTask
        task = AgentTask(
            task_id="m1", description="分析监控",
            context={"metrics": {"p99": 150, "qps": 500}},
        )
        result = await agent.run(task)
        assert result.task_id == "m1"
        assert result.answer

    @pytest.mark.asyncio
    async def test_analyze_metrics(self, agent):
        answer = await agent.analyze_metrics({"p99": 200})
        assert answer

    @pytest.mark.asyncio
    async def test_run_empty_metrics(self, agent):
        from llm.agent.base import AgentTask
        task = AgentTask(task_id="m2", description="test", context={})
        result = await agent.run(task)
        assert result.answer


def test_format_metrics():
    assert _format_metrics({"p99": 150}) == "- p99: 150"
    assert _format_metrics({}) == "暂无监控数据"


# ========== LLM Tasks ==========

class TestContentGenerator:
    @pytest.fixture
    def gen(self):
        return ContentGenerator(MockBackend())

    @pytest.mark.asyncio
    async def test_generate(self, gen):
        result = await gen.generate_simulated_interactions(
            title="测试文章", tags=["Python", "AI"]
        )
        # MockBackend 返回固定文本，JSON 解析可能失败，fallback 为空列表
        assert "simulated_interactions" in result


class TestEmbedder:
    @pytest.fixture
    def embedder(self):
        return Embedder(MockBackend())

    @pytest.mark.asyncio
    async def test_embed_text(self, embedder):
        emb = await embedder.embed_text("hello world")
        assert len(emb) == 128

    @pytest.mark.asyncio
    async def test_embed_batch(self, embedder):
        embs = await embedder.embed_batch(["hello", "world"])
        assert len(embs) == 2

    @pytest.mark.asyncio
    async def test_embed_item(self, embedder):
        emb = await embedder.embed_item("i1", "标题", ["tag1"], "描述")
        assert len(emb) == 128


class TestRerankSummary:
    @pytest.fixture
    def summarizer(self):
        return RerankSummary(MockBackend())

    @pytest.mark.asyncio
    async def test_generate_summary(self, summarizer):
        summary = await summarizer.generate_summary(
            "Python", "一篇Python文章", ["编程", "AI"]
        )
        assert summary  # non-empty

    @pytest.mark.asyncio
    async def test_batch_summarize(self, summarizer):
        items = [{"content": "文章1"}, {"content": "文章2"}]
        summaries = await summarizer.batch_summarize("Python", items, ["编程"])
        assert len(summaries) == 2


class TestSemanticSearch:
    @pytest.fixture
    def search(self):
        return SemanticSearch(MockBackend())

    @pytest.mark.asyncio
    async def test_expand_query(self, search):
        expanded = await search.expand_query("Python教程")
        assert len(expanded) >= 1
        assert expanded[0] == "Python教程"

    @pytest.mark.asyncio
    async def test_semantic_search_no_store(self, search):
        results = await search.semantic_search("test", faiss_store=None)
        assert results == []


# ========== PromptManager ==========

class TestPromptManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return PromptManager(template_dir=tmp_path)

    def test_load_missing_template(self, manager):
        assert manager.load("nonexistent") == ""

    def test_register_and_load(self, manager):
        manager.register("greeting", "Hello {{name}}!")
        assert manager.load("greeting") == "Hello {{name}}!"

    def test_render(self, manager):
        manager.register("greet", "Hello {{name}}, welcome to {{place}}!")
        result = manager.render("greet", name="Alice", place="Wonderland")
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_render_missing_template(self, manager):
        assert manager.render("missing", name="x") == ""

    def test_list_templates(self, manager):
        manager.register("a", "x")
        manager.register("b", "y")
        templates = manager.list_templates()
        assert "a" in templates
        assert "b" in templates

    def test_load_from_file(self, manager, tmp_path):
        (tmp_path / "test.txt").write_text("file template content")
        loaded = manager.load("test")
        assert loaded == "file template content"

    def test_load_caches(self, manager, tmp_path):
        (tmp_path / "cached.txt").write_text("v1")
        manager.load("cached")
        (tmp_path / "cached.txt").write_text("v2")
        assert manager.load("cached") == "v1"  # 缓存命中
