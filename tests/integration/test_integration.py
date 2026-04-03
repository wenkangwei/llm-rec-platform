"""集成测试 — 端到端推荐链路验证

验证完整链路: HTTP Request → RecContext → Pipeline → RecResponse
"""

from __future__ import annotations

import asyncio

import pytest

from protocols.schemas.context import Item, RecContext
from protocols.schemas.converters import (
    context_to_response,
    context_to_search_response,
    request_to_context,
    search_to_context,
)
from protocols.schemas.request import RecRequest, SearchRequest
from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from pipeline.recall.merger import RecallMerger
from pipeline.recall.hot import HotRecall
from pipeline.ranking.rerank import ReRankStage
from pipeline.ranking.mixer import MixerStage


# ===== 测试用 Stage =====

class FakePersonalizedRecall:
    """模拟个性化召回。"""
    def name(self):
        return "personalized"

    def process(self, ctx):
        for i in range(30):
            ctx.candidates.append(Item(
                id=f"pers_{i}", score=0.95 - i * 0.02, source="personalized",
                features={"author_id": f"a{i % 5}", "tags": ["tag1", "tag2"], "content_type": "article"},
            ))
        return ctx

    def warmup(self):
        pass

    def health_check(self):
        return True

    def shutdown(self):
        pass


class FakeCollaborativeRecall:
    """模拟协同过滤召回。"""
    def name(self):
        return "collaborative"

    def process(self, ctx):
        for i in range(20):
            ctx.candidates.append(Item(
                id=f"cf_{i}", score=0.88 - i * 0.02, source="collaborative",
                features={"author_id": f"a{i % 3}", "content_type": "video"},
            ))
        return ctx

    def warmup(self):
        pass

    def health_check(self):
        return True

    def shutdown(self):
        pass


class FakePrerankStage:
    """模拟粗排：过滤低分。"""
    def name(self):
        return "prerank"

    def process(self, ctx):
        ctx.candidates = [item for item in ctx.candidates if item.score > 0.5]
        ctx.candidates = ctx.candidates[:200]
        return ctx


class FakeRankStage:
    """模拟精排：微调分数。"""
    def name(self):
        return "rank"

    def process(self, ctx):
        for item in ctx.candidates:
            item.score *= 0.95  # 微调
        ctx.candidates.sort(key=lambda x: x.score, reverse=True)
        ctx.candidates = ctx.candidates[:50]
        return ctx


class TestEndToEndPipeline:
    """端到端链路集成测试。"""

    def test_full_pipeline(self):
        """完整链路: 召回 → 粗排 → 精排 → 重排 → 混排。"""
        executor = PipelineExecutor()

        # 召回阶段
        merger = RecallMerger()
        merger.register_channel(FakePersonalizedRecall())
        hot = HotRecall(top_k=10)
        hot.update_hot_items([(f"hot_{i}", 100.0 - i) for i in range(10)])
        merger.register_channel(hot)
        merger.register_channel(FakeCollaborativeRecall())
        executor.register(merger)

        # 粗排
        executor.register(FakePrerankStage())
        # 精排
        executor.register(FakeRankStage())
        # 重排
        executor.register(ReRankStage())
        # 混排
        executor.register(MixerStage())

        ctx = create_context(user_id="u1", scene="home_feed", page_size=20)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))

        # 验证结果
        assert len(result.candidates) <= 20
        assert len(result.candidates) > 0
        assert all(isinstance(item, Item) for item in result.candidates)

        # 验证指标记录
        assert len(result.stage_metrics) >= 4  # recall + prerank + rank + rerank + mixer

    def test_request_to_response_flow(self):
        """HTTP Request → RecContext → Pipeline → Response 完整流程。"""
        # 1. 构造 HTTP 请求
        req = RecRequest(user_id="user_123", scene="home_feed", num=10, page=0)

        # 2. 转为内部 RecContext
        ctx = request_to_context(req, "req_test_001")
        assert ctx.user_id == "user_123"
        assert ctx.page_size == 10

        # 3. 执行 Pipeline
        executor = PipelineExecutor()
        merger = RecallMerger()
        hot = HotRecall()
        hot.update_hot_items([(f"item_{i}", 100.0 - i) for i in range(20)])
        merger.register_channel(hot)
        executor.register(merger)
        executor.register(FakePrerankStage())
        executor.register(MixerStage())

        ctx = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))

        # 4. 转为 HTTP Response
        resp = context_to_response(ctx)
        assert resp.request_id == "req_test_001"
        assert len(resp.items) <= 10
        assert all(item.item_id for item in resp.items)
        assert resp.total > 0

    def test_search_flow(self):
        """搜索推荐完整流程。"""
        req = SearchRequest(user_id="u1", query="python教程", num=5)

        ctx = search_to_context(req, "req_search_001")
        assert ctx.scene == "search_feed"
        assert ctx.query == "python教程"

        # 模拟搜索召回
        merger = RecallMerger()
        hot = HotRecall(top_k=10)
        hot.update_hot_items([(f"s_{i}", 1.0 / (i + 1)) for i in range(10)])
        merger.register_channel(hot)

        ctx = merger.process(ctx)
        resp = context_to_search_response(ctx)

        assert resp.query == "python教程"
        assert resp.total > 0

    def test_pipeline_graceful_degradation(self):
        """测试链路降级：单阶段异常时仍然返回结果。"""
        class ErrorPrerank:
            def name(self):
                return "error_prerank"
            def process(self, ctx):
                raise RuntimeError("粗排服务不可用")

        executor = PipelineExecutor()
        merger = RecallMerger()
        hot = HotRecall()
        hot.update_hot_items([(f"h_{i}", 1.0) for i in range(5)])
        merger.register_channel(hot)
        executor.register(merger)
        executor.register(ErrorPrerank())  # 会失败
        executor.register(MixerStage())

        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))

        # 召回结果保留（粗排失败不影响）
        assert len(result.candidates) > 0

    def test_recall_channel_isolation(self):
        """测试召回通道隔离：单个通道失败不影响其他通道。"""
        class ErrorChannel:
            def name(self):
                return "error_channel"
            def process(self, ctx):
                raise RuntimeError("通道故障")

        merger = RecallMerger()
        merger.register_channel(ErrorChannel())
        hot = HotRecall()
        hot.update_hot_items([("h1", 1.0)])
        merger.register_channel(hot)

        ctx = create_context(user_id="u1")
        result = merger.process(ctx)

        # error_channel 失败，hot 正常
        assert any(item.source == "hot" for item in result.candidates)
