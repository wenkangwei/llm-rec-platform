"""共享 fixtures — 所有测试模块共用"""

from __future__ import annotations

import asyncio

import pytest

from llm.backends.mock_backend import MockBackend
from llm.chat.manager import ChatSessionManager
from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from pipeline.recall.hot import HotRecall
from pipeline.recall.merger import RecallMerger
from pipeline.ranking.mixer import MixerStage
from pipeline.ranking.rerank import ReRankStage
from protocols.schemas.context import Item, RecContext


# ===== Event Loop =====

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop，避免每个测试重新创建。"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ===== LLM =====

@pytest.fixture
def mock_backend():
    """MockBackend 实例。"""
    return MockBackend()


@pytest.fixture
def chat_manager(mock_backend):
    """ChatSessionManager 实例。"""
    return ChatSessionManager(mock_backend, pipeline_state={})


# ===== Pipeline =====

@pytest.fixture
def simple_ctx():
    """基础 RecContext。"""
    return create_context(user_id="test_user", scene="home_feed", page_size=20)


@pytest.fixture
def ctx_with_candidates():
    """带候选物品的 RecContext。"""
    items = [
        Item(id=f"item_{i}", score=1.0 - i * 0.05, source="test",
             features={"content_type": "article" if i % 3 else "video",
                       "author_id": f"a{i % 5}",
                       "tags": ["tag1", "tag2"]})
        for i in range(30)
    ]
    return RecContext(
        request_id="test_req", user_id="u1", scene="home_feed",
        page_size=20, candidates=items,
    )


@pytest.fixture
def hot_recall():
    """预装热门物品的 HotRecall。"""
    recall = HotRecall(top_k=10)
    recall.update_hot_items([(f"hot_{i}", 100.0 - i) for i in range(10)])
    return recall


@pytest.fixture
def recall_merger(hot_recall):
    """带 HotRecall 的 RecallMerger。"""
    merger = RecallMerger()
    merger.register_channel(hot_recall)
    return merger


@pytest.fixture
def full_executor(recall_merger):
    """完整 PipelineExecutor（召回→重排→混排）。"""
    executor = PipelineExecutor()
    executor.register(recall_merger)
    executor.register(ReRankStage())
    executor.register(MixerStage())
    return executor
