"""llm 模块单元测试 — MockBackend / ChatSessionManager / Agent"""

from __future__ import annotations

import asyncio

import pytest

from llm.backends.mock_backend import MockBackend
from llm.chat.manager import ChatSessionManager
from llm.chat.schemas import IntentType


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
        intent = manager._classify_intent("关闭热门召回通道")
        assert intent.type == IntentType.STRATEGY

    def test_monitor_intent(self, manager):
        intent = manager._classify_intent("今天P99延迟多少")
        assert intent.type == IntentType.MONITOR

    def test_debug_intent(self, manager):
        intent = manager._classify_intent("分析一下用户123的推荐结果为什么偏少")
        assert intent.type == IntentType.DEBUG

    def test_config_intent(self, manager):
        intent = manager._classify_intent("配置参数和环境变量")
        assert intent.type == IntentType.CONFIG

    def test_unknown_intent(self, manager):
        intent = manager._classify_intent("你好世界")
        assert intent.type == IntentType.UNKNOWN

    def test_entity_extraction_user(self, manager):
        entities = manager._extract_entities("分析用户abc123")
        assert entities.get("user_id") == "abc123"

    def test_entity_extraction_number(self, manager):
        entities = manager._extract_entities("权重调到0.3")
        assert entities.get("value") == 0.3
