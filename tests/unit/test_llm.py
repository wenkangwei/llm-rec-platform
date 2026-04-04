"""llm 模块单元测试 — MockBackend / ChatSessionManager / Agent / Factory"""

from __future__ import annotations

import asyncio
import time

import pytest

from llm.backends.mock_backend import MockBackend
from llm.chat.manager import ChatSessionManager
from llm.chat.schemas import IntentType
from llm.factory import LLMFactory


class TestMockBackend:
    """MockBackend 测试。"""

    @pytest.fixture
    def backend(self):
        return MockBackend()

    def test_init(self, backend):
        assert backend is not None

    @pytest.mark.asyncio
    async def test_generate(self, backend):
        result = await backend.generate("hello")
        assert "[Mock Response]" in result

    @pytest.mark.asyncio
    async def test_embed_single(self, backend):
        result = await backend.embed("hello")
        assert len(result) == 1
        assert len(result[0]) == 128

    @pytest.mark.asyncio
    async def test_embed_batch(self, backend):
        result = await backend.embed(["hello", "world"])
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_health_check(self, backend):
        assert await backend.health_check() is True

    @pytest.mark.asyncio
    async def test_warmup(self, backend):
        await backend.warmup()  # 不抛异常即可


class TestChatSessionManager:
    """ChatSessionManager 测试。"""

    @pytest.fixture
    def manager(self):
        backend = MockBackend()
        return ChatSessionManager(backend, pipeline_state={})

    def test_create_session(self, manager):
        session = manager.create_session("user1")
        assert session.user_id == "user1"
        assert session.session_id

    def test_get_session(self, manager):
        session = manager.create_session("user1")
        found = manager.get_session(session.session_id)
        assert found is session

    def test_get_missing_session(self, manager):
        assert manager.get_session("nonexistent") is None

    @pytest.mark.asyncio
    async def test_chat_invalid_session(self, manager):
        result = await manager.chat("nonexistent", "hello")
        assert "不存在" in result

    @pytest.mark.asyncio
    async def test_chat_strategy_intent(self, manager):
        session = manager.create_session("user1")
        result = await manager.chat(session.session_id, "关闭热门召回通道")
        assert result  # 有返回内容

    @pytest.mark.asyncio
    async def test_chat_monitor_intent(self, manager):
        session = manager.create_session("user1")
        result = await manager.chat(session.session_id, "今天P99延迟多少")
        assert result

    @pytest.mark.asyncio
    async def test_chat_unknown_intent(self, manager):
        session = manager.create_session("user1")
        result = await manager.chat(session.session_id, "你好")
        assert result

    @pytest.mark.asyncio
    async def test_session_history(self, manager):
        session = manager.create_session("user1")
        await manager.chat(session.session_id, "hello")
        assert len(session.messages) == 2  # user + assistant


class TestIntentClassification:
    """意图分类测试。"""

    @pytest.fixture
    def manager(self):
        backend = MockBackend()
        return ChatSessionManager(backend, pipeline_state={})

    def test_strategy_intent(self, manager):
        intent = manager._classify_intent_keyword("关闭热门召回通道")
        assert intent.type == IntentType.STRATEGY

    def test_monitor_intent(self, manager):
        intent = manager._classify_intent_keyword("今天P99延迟多少")
        assert intent.type == IntentType.MONITOR

    def test_debug_intent(self, manager):
        intent = manager._classify_intent_keyword("分析一下用户123的推荐结果为什么偏少")
        assert intent.type == IntentType.DEBUG

    def test_config_intent(self, manager):
        intent = manager._classify_intent_keyword("配置参数和环境变量")
        assert intent.type == IntentType.CONFIG

    def test_unknown_intent(self, manager):
        intent = manager._classify_intent_keyword("你好世界")
        assert intent.type == IntentType.UNKNOWN

    def test_parse_intent_response_valid(self, manager):
        response = '{"intent": "monitor", "confidence": 0.95, "reason": "查询延迟指标"}'
        intent = manager._parse_intent_response(response, "P99延迟多少")
        assert intent.type == IntentType.MONITOR
        assert intent.confidence == 0.95

    def test_parse_intent_response_with_extra_text(self, manager):
        response = '好的，分析结果如下：\n{"intent": "strategy", "confidence": 0.8, "reason": "关闭通道"}\n请查收'
        intent = manager._parse_intent_response(response, "关闭通道")
        assert intent.type == IntentType.STRATEGY

    def test_parse_intent_response_invalid_json(self, manager):
        intent = manager._parse_intent_response("not json at all", "关闭通道")
        # 降级到关键词匹配
        assert intent.type == IntentType.STRATEGY

    def test_parse_intent_response_unknown_intent(self, manager):
        response = '{"intent": "unknown", "confidence": 0.9, "reason": "闲聊"}'
        intent = manager._parse_intent_response(response, "你好")
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_classify_intent_llm_with_mock(self, manager):
        """LLM 意图识别 + Mock 后端测试。"""
        intent = await manager._classify_intent_llm("查看系统延迟指标")
        # MockBackend 会返回固定文本，解析失败降级到关键词
        # "延迟" 关键词命中 MONITOR
        assert intent.type == IntentType.MONITOR

    def test_entity_extraction_user(self, manager):
        entities = manager._extract_entities("分析用户abc123")
        assert entities.get("user_id") == "abc123"

    def test_entity_extraction_number(self, manager):
        entities = manager._extract_entities("权重调到0.3")
        assert entities.get("value") == 0.3


class TestChatSessionExpiry:
    """会话过期和淘汰测试。"""

    @pytest.fixture
    def manager(self):
        return ChatSessionManager(MockBackend(), pipeline_state={}, session_ttl=1, max_sessions=3)

    def test_expired_session_returns_none(self, manager):
        session = manager.create_session("user1")
        session.updated_at = time.time() - 10  # 已过期
        assert manager.get_session(session.session_id) is None

    def test_cleanup_expired(self, manager):
        s1 = manager.create_session("u1")
        s2 = manager.create_session("u2")
        s1.updated_at = time.time() - 10
        count = manager.cleanup_expired_sessions()
        assert count == 1
        assert manager.get_session(s2.session_id) is not None

    def test_max_sessions_eviction(self, manager):
        sessions = [manager.create_session(f"u{i}") for i in range(4)]
        # max_sessions=3, 创建第 4 个时淘汰最旧
        assert len(manager._sessions) == 3


class TestLLMFactory:
    """LLM Factory 测试。"""

    def test_create_mock(self):
        backend = LLMFactory.create({"type": "mock"})
        assert isinstance(backend, MockBackend)

    def test_create_vllm_requires_base_url(self):
        with pytest.raises(ValueError, match="base_url"):
            LLMFactory.create({"type": "openai_compatible"})

    def test_create_vllm_with_config(self):
        backend = LLMFactory.create({
            "type": "openai_compatible",
            "base_url": "http://vllm:8000/v1",
            "api_key": "test-key",
        })
        assert backend._base_url == "http://vllm:8000/v1"
        assert backend._api_key == "test-key"

    def test_create_unsupported_type(self):
        with pytest.raises(ValueError, match="不支持"):
            LLMFactory.create({"type": "nonexistent_backend"})
