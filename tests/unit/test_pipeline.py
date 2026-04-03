"""pipeline 模块单元测试 — PipelineStage / Context / Executor / Recall / Ranking"""

from __future__ import annotations

import asyncio

import pytest

from pipeline.base import PipelineStage
from pipeline.context import (
    add_stage_metrics,
    create_context,
    dedup_items,
    get_items_by_source,
    sort_by_score,
    truncate_candidates,
)
from pipeline.executor import PipelineExecutor
from protocols.schemas.context import Item, RecContext


# ===== 测试用 Mock Stage =====

class FakeRecallStage(PipelineStage):
    def __init__(self, items: list[Item] | None = None, name_str: str = "fake_recall"):
        self._items = items or []
        self._name = name_str

    def name(self) -> str:
        return self._name

    def process(self, ctx: RecContext) -> RecContext:
        for item in self._items:
            ctx.candidates.append(Item(id=item.id, score=item.score, source=self._name))
        return ctx


class FakeRankStage(PipelineStage):
    def name(self) -> str:
        return "fake_rank"

    def process(self, ctx: RecContext) -> RecContext:
        ctx.candidates = [item for item in ctx.candidates if item.score > 0.5]
        return ctx


class ErrorStage(PipelineStage):
    def name(self) -> str:
        return "error_stage"

    def process(self, ctx: RecContext) -> RecContext:
        raise RuntimeError("stage error")


# ===== Context 工具函数 =====

class TestContextUtils:
    def test_create_context(self):
        ctx = create_context(user_id="u1", scene="home_feed")
        assert ctx.user_id == "u1"
        assert ctx.request_id
        assert ctx.candidates == []

    def test_create_context_with_query(self):
        ctx = create_context(user_id="u1", scene="search_feed", query="python")
        assert ctx.query == "python"

    def test_dedup_items(self):
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[
                Item(id="i1", score=0.9, source="a"),
                Item(id="i1", score=0.8, source="b"),
                Item(id="i2", score=0.7, source="a"),
            ],
        )
        dedup_items(ctx)
        assert len(ctx.candidates) == 2
        # 保留高分
        assert ctx.candidates[0].id == "i1" or any(c.id == "i1" and c.score == 0.9 for c in ctx.candidates)

    def test_sort_by_score(self):
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[
                Item(id="i1", score=0.5),
                Item(id="i2", score=0.9),
                Item(id="i3", score=0.7),
            ],
        )
        sort_by_score(ctx)
        assert ctx.candidates[0].id == "i2"
        assert ctx.candidates[1].id == "i3"

    def test_truncate_candidates(self):
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[Item(id=f"i{i}", score=1.0) for i in range(100)],
        )
        truncate_candidates(ctx, 20)
        assert len(ctx.candidates) == 20

    def test_get_items_by_source(self):
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[
                Item(id="i1", score=0.9, source="hot"),
                Item(id="i2", score=0.8, source="cf"),
                Item(id="i3", score=0.7, source="hot"),
            ],
        )
        hot_items = get_items_by_source(ctx, "hot")
        assert len(hot_items) == 2

    def test_add_stage_metrics(self):
        ctx = create_context(user_id="u1")
        add_stage_metrics(ctx, "recall", 10.5, 0, 500)
        assert len(ctx.stage_metrics) == 1
        assert ctx.stage_metrics[0].stage_name == "recall"


# ===== PipelineStage 基类 =====

class TestPipelineStage:
    def test_invoke_calls_process(self):
        items = [Item(id="i1", score=0.9)]
        stage = FakeRecallStage(items, "test")
        ctx = create_context(user_id="u1")
        result = stage.invoke(ctx)
        assert len(result.candidates) == 1

    def test_ainvoke(self):
        items = [Item(id="i1", score=0.9)]
        stage = FakeRecallStage(items, "test")
        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(stage.ainvoke(ctx))
        assert len(result.candidates) == 1

    def test_grpc_not_implemented(self):
        stage = FakeRecallStage()
        with pytest.raises(NotImplementedError):
            stage.process_grpc(b"")

    def test_grpc_servicable_false(self):
        stage = FakeRecallStage()
        assert stage.grpc_servicable is False

    def test_health_check_default(self):
        stage = FakeRecallStage()
        assert stage.health_check() is True


# ===== PipelineExecutor =====

class TestPipelineExecutor:
    def test_register_and_execute(self):
        executor = PipelineExecutor()
        recall = FakeRecallStage(
            [Item(id="i1", score=0.9), Item(id="i2", score=0.3)],
            "recall",
        )
        rank = FakeRankStage()
        executor.register(recall)
        executor.register(rank)

        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))
        assert len(result.candidates) == 1  # score > 0.5
        assert result.candidates[0].id == "i1"

    def test_error_stage_isolation(self):
        """单阶段失败不阻塞链路，且标记降级。"""
        executor = PipelineExecutor()
        error = ErrorStage()
        recall = FakeRecallStage([Item(id="i1", score=0.9)], "recall")
        executor.register(error)
        executor.register(recall)

        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))
        # error_stage 失败但 recall 仍然执行
        assert len(result.candidates) == 1
        # 降级标记
        assert result.degraded is True
        assert "error_stage" in result.degraded_stages

    def test_no_degradation_when_all_succeed(self):
        """全部成功时无降级标记。"""
        executor = PipelineExecutor()
        recall = FakeRecallStage([Item(id="i1", score=0.9)], "recall")
        executor.register(recall)

        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))
        assert result.degraded is False
        assert result.degraded_stages == []

    def test_stage_metrics_recorded(self):
        executor = PipelineExecutor()
        recall = FakeRecallStage([Item(id="i1", score=0.9)], "recall")
        executor.register(recall)

        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))
        assert len(result.stage_metrics) == 1
        assert result.stage_metrics[0].stage_name == "recall"
        assert result.stage_metrics[0].latency_ms > 0

    def test_health_check(self):
        executor = PipelineExecutor()
        executor.register(FakeRecallStage(name_str="recall"))
        health = executor.health_check()
        assert health["recall"] is True

    def test_load_from_config(self):
        executor = PipelineExecutor()
        configs = [
            {"name": "recall", "class": "tests.unit.test_pipeline.FakeRecallStage"},
        ]
        executor.load_from_config(configs)
        ctx = create_context(user_id="u1")
        result = asyncio.get_event_loop().run_until_complete(executor.execute(ctx))
        assert len(result.stage_metrics) == 1


# ===== RecallMerger =====

class TestRecallMerger:
    def test_merge_multiple_channels(self):
        from pipeline.recall.merger import RecallMerger

        merger = RecallMerger()
        merger.register_channel(FakeRecallStage(
            [Item(id="i1", score=0.9), Item(id="i2", score=0.8)],
            "hot",
        ))
        merger.register_channel(FakeRecallStage(
            [Item(id="i2", score=0.85), Item(id="i3", score=0.7)],
            "cf",
        ))

        ctx = create_context(user_id="u1")
        result = merger.process(ctx)

        # 去重后 3 个
        assert len(result.candidates) == 3
        # 按分数排序
        assert result.candidates[0].score >= result.candidates[1].score

    def test_source_stats(self):
        from pipeline.recall.merger import RecallMerger

        merger = RecallMerger()
        merger.register_channel(FakeRecallStage(
            [Item(id="i1", score=0.9)],
            "hot",
        ))

        ctx = create_context(user_id="u1")
        result = merger.process(ctx)
        assert result.extras["recall_sources"]["hot"] == 1

    def test_channel_error_isolation(self):
        from pipeline.recall.merger import RecallMerger

        merger = RecallMerger()
        merger.register_channel(ErrorStage())
        merger.register_channel(FakeRecallStage(
            [Item(id="i1", score=0.9)],
            "hot",
        ))

        ctx = create_context(user_id="u1")
        result = merger.process(ctx)
        assert len(result.candidates) == 1  # error_stage 失败，hot 正常


# ===== HotRecall =====

class TestHotRecall:
    def test_empty_hot_items(self):
        from pipeline.recall.hot import HotRecall

        recall = HotRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0

    def test_with_hot_items(self):
        from pipeline.recall.hot import HotRecall

        recall = HotRecall(top_k=2)
        recall.update_hot_items([("h1", 100.0), ("h2", 90.0), ("h3", 80.0)])

        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 2
        assert result.candidates[0].source == "hot"


# ===== ReRankStage =====

class TestReRankStage:
    def test_dedup(self):
        from pipeline.ranking.rerank import ReRankStage

        rerank = ReRankStage()
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[
                Item(id="i1", score=0.9),
                Item(id="i1", score=0.8),
            ],
        )
        result = rerank.process(ctx)
        ids = [item.id for item in result.candidates]
        assert len(set(ids)) == len(ids)

    def test_fatigue_filter(self):
        from pipeline.ranking.rerank import ReRankStage

        rerank = ReRankStage()
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[
                Item(id="i1", score=0.9),
                Item(id="i2", score=0.8),
            ],
            user_features={"recent_exposed_items": ["i1"]},
        )
        result = rerank.process(ctx)
        assert all(item.id != "i1" for item in result.candidates)

    def test_empty_candidates(self):
        from pipeline.ranking.rerank import ReRankStage

        rerank = ReRankStage()
        ctx = create_context(user_id="u1")
        result = rerank.process(ctx)
        assert len(result.candidates) == 0


# ===== MixerStage =====

class TestMixerStage:
    def test_weighted_round_robin(self):
        from pipeline.ranking.mixer import MixerStage

        mixer = MixerStage(strategy="weighted_round_robin")
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed", page_size=10,
            candidates=[
                Item(id=f"a{i}", score=1.0 - i * 0.01, source="s", features={"content_type": "article"})
                for i in range(5)
            ] + [
                Item(id=f"v{i}", score=0.9 - i * 0.01, source="s", features={"content_type": "video"})
                for i in range(3)
            ] + [
                Item(id=f"p{i}", score=0.8 - i * 0.01, source="s", features={"content_type": "post"})
                for i in range(2)
            ],
        )
        result = mixer.process(ctx)
        types = [item.features.get("content_type") for item in result.candidates]
        assert "article" in types
        assert len(result.candidates) <= 10

    def test_empty_candidates(self):
        from pipeline.ranking.mixer import MixerStage

        mixer = MixerStage()
        ctx = create_context(user_id="u1")
        result = mixer.process(ctx)
        assert len(result.candidates) == 0
