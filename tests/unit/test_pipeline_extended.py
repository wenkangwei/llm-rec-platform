"""pipeline 扩展模块测试 — recall 子模块 / ranking / scenes / model backends"""

from __future__ import annotations

import pytest

from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from pipeline.base import PipelineStage
from protocols.schemas.context import Item, RecContext


# ===== Recall 子模块 =====

class TestCollaborativeRecall:
    def test_name(self):
        from pipeline.recall.collaborative import CollaborativeRecall
        recall = CollaborativeRecall()
        assert recall.name() == "collaborative"

    def test_process_no_history(self):
        from pipeline.recall.collaborative import CollaborativeRecall
        recall = CollaborativeRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0

    def test_process_with_similarity_matrix(self):
        from pipeline.recall.collaborative import CollaborativeRecall
        recall = CollaborativeRecall()
        recall._similarity_matrix = {"item1": [("item2", 0.9), ("item3", 0.8)]}
        ctx = create_context(user_id="u1")
        ctx.user_features = {"recent_click_items": ["item1"]}
        result = recall.process(ctx)
        assert len(result.candidates) == 2
        assert result.candidates[0].source == "collaborative"


class TestCommunityRecall:
    def test_name(self):
        from pipeline.recall.community import CommunityRecall
        recall = CommunityRecall()
        assert recall.name() == "community"

    def test_process_no_communities(self):
        from pipeline.recall.community import CommunityRecall
        recall = CommunityRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0

    def test_process_with_communities(self):
        from pipeline.recall.community import CommunityRecall
        recall = CommunityRecall()
        ctx = create_context(user_id="u1")
        ctx.user_features = {"community_ids": ["c1"]}
        result = recall.process(ctx)
        assert isinstance(result.candidates, list)


class TestSocialRecall:
    def test_name(self):
        from pipeline.recall.social import SocialRecall
        recall = SocialRecall()
        assert recall.name() == "social"

    def test_process_no_following(self):
        from pipeline.recall.social import SocialRecall
        recall = SocialRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0

    def test_process_with_following(self):
        from pipeline.recall.social import SocialRecall
        recall = SocialRecall()
        ctx = create_context(user_id="u1")
        ctx.user_features = {"following_ids": ["u2", "u3"]}
        result = recall.process(ctx)
        assert isinstance(result.candidates, list)


class TestColdStartRecall:
    def test_name(self):
        from pipeline.recall.cold_start import ColdStartRecall
        recall = ColdStartRecall()
        assert recall.name() == "cold_start"

    def test_process_new_user(self):
        from pipeline.recall.cold_start import ColdStartRecall
        recall = ColdStartRecall()
        ctx = create_context(user_id="u1")
        ctx.user_features = {"cold_start": True}
        result = recall.process(ctx)
        assert isinstance(result.candidates, list)

    def test_process_existing_user_new_items(self):
        from pipeline.recall.cold_start import ColdStartRecall
        recall = ColdStartRecall()
        recall.update_new_items([("new1", 0.8), ("new2", 0.7)])
        ctx = create_context(user_id="u1")
        ctx.user_features = {"cold_start": False}
        result = recall.process(ctx)
        assert len(result.candidates) == 2
        assert result.candidates[0].score == pytest.approx(0.8 * 1.2)

    def test_update_new_items(self):
        from pipeline.recall.cold_start import ColdStartRecall
        recall = ColdStartRecall()
        recall.update_new_items([("i1", 0.5)])
        assert len(recall._new_items) == 1


class TestPersonalizedRecall:
    def test_name(self):
        from pipeline.recall.personalized import PersonalizedRecall
        recall = PersonalizedRecall()
        assert recall.name() == "personalized"

    def test_process_no_embedding(self):
        from pipeline.recall.personalized import PersonalizedRecall
        recall = PersonalizedRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0


class TestOperatorRecall:
    def test_name(self):
        from pipeline.recall.operator import OperatorRecall
        recall = OperatorRecall()
        assert recall.name() == "operator"

    def test_process_no_pinned(self):
        from pipeline.recall.operator import OperatorRecall
        recall = OperatorRecall()
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 0

    def test_process_with_pinned(self):
        from pipeline.recall.operator import OperatorRecall
        recall = OperatorRecall(top_k=2)
        recall.update_pinned([("p1", 1.0), ("p2", 0.9), ("p3", 0.8)])
        ctx = create_context(user_id="u1")
        result = recall.process(ctx)
        assert len(result.candidates) == 2
        assert result.candidates[0].source == "operator"

    def test_update_pinned(self):
        from pipeline.recall.operator import OperatorRecall
        recall = OperatorRecall()
        recall.update_pinned([("i1", 0.5)])
        assert len(recall._pinned_items) == 1


# ===== Ranking =====

class TestPreRankStage:
    def test_name(self):
        from pipeline.ranking.prerank import PreRankStage
        stage = PreRankStage()
        assert stage.name() == "prerank"

    def test_process_returns_context(self):
        from pipeline.ranking.prerank import PreRankStage
        stage = PreRankStage(score_threshold=0.5, max_candidates=10)
        ctx = create_context(user_id="u1")
        ctx.candidates = [
            Item(id="i1", score=0.9),
            Item(id="i2", score=0.3),
            Item(id="i3", score=0.6),
        ]
        result = stage.process(ctx)
        assert isinstance(result.candidates, list)

    def test_warmup(self):
        from pipeline.ranking.prerank import PreRankStage
        stage = PreRankStage()
        stage.warmup()


class TestRankStage:
    def test_name(self):
        from pipeline.ranking.rank import RankStage
        stage = RankStage()
        assert stage.name() == "rank"

    def test_cosine_sim(self):
        from pipeline.ranking.rank import RankStage
        sim = RankStage._cosine_sim([1, 0, 0], [0, 1, 0])
        assert sim == pytest.approx(0.0)
        sim2 = RankStage._cosine_sim([1, 0, 0], [1, 0, 0])
        assert sim2 == pytest.approx(1.0)

    def test_process(self):
        from pipeline.ranking.rank import RankStage
        stage = RankStage(max_candidates=10)
        ctx = create_context(user_id="u1")
        ctx.candidates = [Item(id=f"i{i}", score=0.5 + i * 0.01) for i in range(5)]
        result = stage.process(ctx)
        assert isinstance(result.candidates, list)


# ===== Scenes =====

class _DummyStage(PipelineStage):
    def __init__(self, name_str="dummy"):
        self._name = name_str

    def name(self) -> str:
        return self._name

    def process(self, ctx: RecContext) -> RecContext:
        return ctx


def _make_executor():
    executor = PipelineExecutor()
    executor.register(_DummyStage("recall"))
    executor.register(_DummyStage("rank"))
    return executor


class TestHomeFeedScene:
    @pytest.mark.asyncio
    async def test_recommend(self):
        from pipeline.scene.home_feed import HomeFeedScene
        scene = HomeFeedScene(_make_executor())
        ctx = await scene.recommend("u1", page=0, page_size=10)
        assert ctx.user_id == "u1"
        assert ctx.scene == "home_feed"

    @pytest.mark.asyncio
    async def test_recommend_with_features(self):
        from pipeline.scene.home_feed import HomeFeedScene
        scene = HomeFeedScene(_make_executor())
        ctx = await scene.recommend("u1", user_features={"age": 25})
        assert ctx.user_features.get("age") == 25


class TestSearchFeedScene:
    @pytest.mark.asyncio
    async def test_search(self):
        from pipeline.scene.search_feed import SearchFeedScene
        scene = SearchFeedScene(_make_executor())
        ctx = await scene.search("u1", "Python教程")
        assert ctx.query == "Python教程"
        assert ctx.scene == "search_feed"


class TestFollowFeedScene:
    @pytest.mark.asyncio
    async def test_recommend(self):
        from pipeline.scene.follow_feed import FollowFeedScene
        scene = FollowFeedScene(_make_executor())
        ctx = await scene.recommend("u1")
        assert ctx.scene == "follow_feed"


class TestCommunityFeedScene:
    @pytest.mark.asyncio
    async def test_recommend_with_community(self):
        from pipeline.scene.community_feed import CommunityFeedScene
        scene = CommunityFeedScene(_make_executor())
        ctx = await scene.recommend("u1", community_id="c1")
        assert ctx.scene == "community_feed"
        assert ctx.extras.get("community_id") == "c1"

    @pytest.mark.asyncio
    async def test_recommend_without_community(self):
        from pipeline.scene.community_feed import CommunityFeedScene
        scene = CommunityFeedScene(_make_executor())
        ctx = await scene.recommend("u1")
        assert ctx.scene == "community_feed"


# ===== Model Service Backends =====

class TestBatchProcessor:
    @pytest.mark.asyncio
    async def test_predict(self):
        from pipeline.model_service.backends.batch_processor import BatchProcessor
        from tests.unit.test_model_service import _DummyModel
        import numpy as np

        model = _DummyModel()
        processor = BatchProcessor(model, max_batch_size=4, max_wait_ms=0.01)
        features = np.random.rand(2, 5)
        result = await processor.predict(features)
        assert result.shape == (2,)
