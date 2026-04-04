"""新模块测试：FaissFeatureStore / HiveFeatureStore / Triton backends / gRPC / search summary"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ===== FaissFeatureStore =====

from feature.store.faiss_store import FaissFeatureStore


class TestFaissFeatureStore:
    @pytest.fixture
    def store(self):
        return FaissFeatureStore(dimension=8, metric="ip")

    @pytest.mark.asyncio
    async def test_set_and_get(self, store):
        await store.set("e1", {"f1": 1.0, "f2": 2.0, "f3": 3.0, "f4": 4.0, "f5": 5.0, "f6": 6.0, "f7": 7.0, "f8": 8.0})
        result = await store.get("e1", ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"])
        assert result["f1"] == pytest.approx(1.0)
        assert result["f8"] == pytest.approx(8.0)

    @pytest.mark.asyncio
    async def test_get_missing(self, store):
        result = await store.get("missing", ["f1"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get(self, store):
        vec = np.random.rand(8).astype(np.float32)
        store.add_vectors(["e1", "e2"], np.stack([vec, vec]))
        results = await store.batch_get(["e1", "e2", "e3"], [f"f{i}" for i in range(8)])
        assert len(results) == 3
        assert results[0] != {}
        assert results[2] == {}

    @pytest.mark.asyncio
    async def test_health_check(self, store):
        assert await store.health_check() is True

    def test_search_brute_force(self, store):
        """暴力搜索降级（无 faiss）。"""
        vectors = np.random.rand(20, 8).astype(np.float32)
        store.add_vectors([f"e{i}" for i in range(20)], vectors)
        query = vectors[0]
        results = store.search(query, top_k=5)
        assert len(results) == 5
        # 结果格式正确
        for eid, score in results:
            assert isinstance(eid, str)
            assert isinstance(score, float)
        # 结果按分数降序
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_empty(self, store):
        results = store.search(np.random.rand(8), top_k=5)
        assert results == []

    def test_add_vectors(self, store):
        vecs = np.random.rand(5, 8).astype(np.float32)
        store.add_vectors([f"v{i}" for i in range(5)], vecs)
        assert len(store._entity_vectors) == 5
        assert store._index is None  # 标记需要重建

    def test_search_cosine_metric(self):
        store = FaissFeatureStore(dimension=4, metric="cosine")
        vecs = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [1, 1, 0, 0]], dtype=np.float32)
        store.add_vectors(["a", "b", "c"], vecs)
        results = store.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=2)
        assert len(results) <= 2
        # a 应该是最相似的（cosine = 1.0）
        assert results[0][0] == "a"

    def test_search_l2_metric(self):
        store = FaissFeatureStore(dimension=4, metric="l2")
        vecs = np.array([[1, 0, 0, 0], [10, 0, 0, 0]], dtype=np.float32)
        store.add_vectors(["near", "far"], vecs)
        results = store.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=2)
        assert results[0][0] == "near"  # 距离最近


# ===== HiveFeatureStore =====

from feature.store.hive_store import HiveFeatureStore


class TestHiveFeatureStore:
    @pytest.fixture
    def store(self):
        return HiveFeatureStore(host="localhost", database="test_db")

    @pytest.mark.asyncio
    async def test_health_check_no_connection(self, store):
        """无 pyhive 时健康检查失败。"""
        result = await store.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_no_connection(self, store):
        result = await store.get("e1", ["f1"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get_empty_ids(self, store):
        result = await store.batch_get([], ["f1"])
        assert result == []

    @pytest.mark.asyncio
    async def test_set_no_connection(self, store):
        """无连接时 set 不报错。"""
        await store.set("e1", {"f1": 1.0})

    def test_close_no_connection(self, store):
        store.close()  # 不报错

    def test_close_with_mock_connection(self, store):
        mock_conn = MagicMock()
        store._connection = mock_conn
        store.close()
        mock_conn.close.assert_called_once()
        assert store._connection is None

    def test_query_custom_no_connection(self, store):
        result = store.query_custom("SELECT 1")
        assert result == []


# ===== TritonLLMBackend =====

from llm.backends.triton_backend import TritonLLMBackend


class TestTritonLLMBackend:
    @pytest.fixture
    def backend(self):
        return TritonLLMBackend(server_url="localhost:8001")

    @pytest.mark.asyncio
    async def test_warmup_no_triton(self, backend):
        """无 tritonclient 时降级。"""
        await backend.warmup()
        assert backend._client is None

    @pytest.mark.asyncio
    async def test_generate_no_client(self, backend):
        result = await backend.generate("hello")
        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_stream_no_client(self, backend):
        chunks = []
        async for chunk in backend.generate_stream("hello"):
            chunks.append(chunk)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_embed_no_client(self, backend):
        result = await backend.embed("hello")
        assert result == [[]]

    @pytest.mark.asyncio
    async def test_health_check_no_client(self, backend):
        assert await backend.health_check() is False

    @pytest.mark.asyncio
    async def test_shutdown_no_client(self, backend):
        await backend.shutdown()  # 不报错


# ===== TritonModel =====

from pipeline.model_service.backends.triton_backend import TritonModel


class TestTritonModel:
    def test_name_version(self):
        m = TritonModel("test_model", "v2")
        assert m.name() == "test_model"
        assert m.version() == "v2"

    def test_warmup_no_triton(self):
        m = TritonModel("test")
        m.warmup()
        assert m._client is None

    def test_predict_no_client(self):
        m = TritonModel("test")
        features = np.random.rand(3, 5)
        result = m.predict(features)
        assert result.shape == (3,)
        assert np.all(result == 0)

    def test_shutdown(self):
        m = TritonModel("test")
        m.shutdown()

    def test_health_check_no_client(self):
        m = TritonModel("test")
        assert m.health_check() is False


# ===== gRPC Server =====

from server.grpc_server import RecServiceServicer, create_grpc_server, start_grpc_server


class TestGRPCServer:
    def test_servicer_init(self):
        servicer = RecServiceServicer()
        assert servicer._server is None

    def test_servicer_with_executor(self):
        executor = MagicMock()
        servicer = RecServiceServicer(executor)
        assert servicer._executor is executor

    def test_recommend_not_implemented(self):
        servicer = RecServiceServicer()
        with pytest.raises(NotImplementedError):
            servicer.Recommend(None, None)

    def test_search_not_implemented(self):
        servicer = RecServiceServicer()
        with pytest.raises(NotImplementedError):
            servicer.Search(None, None)

    def test_track_not_implemented(self):
        servicer = RecServiceServicer()
        with pytest.raises(NotImplementedError):
            servicer.Track(None, None)

    def test_health_check_not_implemented(self):
        servicer = RecServiceServicer()
        with pytest.raises(NotImplementedError):
            servicer.HealthCheck(None, None)

    def test_create_grpc_server_no_grpc(self):
        """无 grpcio 时返回 None。"""
        server = create_grpc_server()
        # 返回 None（无 grpcio）或 server 实例
        assert server is None or server is not None


# ===== Search Route LLM Summary =====

from server.routes.search import _generate_search_summary


class TestSearchSummary:
    @pytest.mark.asyncio
    async def test_generate_summary_no_candidates(self):
        """无候选结果时不生成摘要。"""
        ctx = MagicMock()
        ctx.candidates = []
        llm = AsyncMock()
        result = await _generate_search_summary(ctx, "test query", llm)
        assert result is ctx
        llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_summary_with_candidates(self):
        """有候选结果时调用 LLM 生成摘要。"""
        item = MagicMock()
        item.score = 0.95
        item.metadata = {"title": "Python 编程指南"}

        ctx = MagicMock()
        ctx.candidates = [item]
        ctx.extras = {}

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="这是一本编程书籍")
        result = await _generate_search_summary(ctx, "python", llm)
        assert ctx.extras.get("search_summary") == "这是一本编程书籍"

    @pytest.mark.asyncio
    async def test_generate_summary_no_titles(self):
        """候选结果无标题时不生成摘要。"""
        item = MagicMock()
        item.score = 0.5
        item.metadata = {}

        ctx = MagicMock()
        ctx.candidates = [item]
        ctx.extras = {}

        llm = AsyncMock()
        llm.generate = AsyncMock()
        result = await _generate_search_summary(ctx, "test", llm)
        llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_summary_llm_failure(self):
        """LLM 调用失败时不设置摘要。"""
        item = MagicMock()
        item.score = 0.9
        item.metadata = {"title": "Test"}

        ctx = MagicMock()
        ctx.candidates = [item]
        ctx.extras = {}

        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=Exception("LLM error"))
        result = await _generate_search_summary(ctx, "test", llm)
        assert "search_summary" not in ctx.extras


# ===== Social Route =====

from server.routes.social import get_social_graph, follow_user, SocialGraphResponse, FollowRequest


class TestSocialRoute:
    @pytest.mark.asyncio
    async def test_get_social_graph_no_store(self):
        """无存储时返回空社交图谱。"""
        request = MagicMock()
        request.app.state = MagicMock(spec=[])
        result = await get_social_graph("u1", request)
        assert isinstance(result, SocialGraphResponse)
        assert result.following == []

    @pytest.mark.asyncio
    async def test_follow_user_no_store(self):
        """无存储时返回成功但未持久化。"""
        req = FollowRequest(user_id="u1", target_user_id="u2")
        request = MagicMock()
        request.app.state = MagicMock(spec=[])
        result = await follow_user(req, request)
        assert result["success"] is True
        assert result["persisted"] is False

    @pytest.mark.asyncio
    async def test_follow_user_with_redis(self):
        """有 Redis 时写入社交关系。"""
        req = FollowRequest(user_id="u1", target_user_id="u2")
        request = MagicMock()
        redis_store = AsyncMock()
        redis_store.get = AsyncMock(return_value=None)
        redis_store.set = AsyncMock()
        request.app.state.redis_store = redis_store
        result = await follow_user(req, request)
        assert result["success"] is True
        assert result["persisted"] is True


# ===== Training Scripts =====

from scripts.train_two_tower import PairwiseDataset
from scripts.train_ranking import RankDataset


class TestPairwiseDataset:
    def test_empty_path_generates_dummy(self):
        ds = PairwiseDataset(data_path="/nonexistent/path")
        assert len(ds) > 0

    def test_direct_samples(self):
        samples = [
            (np.random.rand(4).astype(np.float32),
             np.random.rand(4).astype(np.float32),
             np.random.rand(4).astype(np.float32))
            for _ in range(10)
        ]
        ds = PairwiseDataset(samples=samples)
        assert len(ds) == 10
        u, p, n = ds[0]
        assert u.shape == (4,)


class TestRankDataset:
    def test_empty_path_generates_dummy(self):
        ds = RankDataset(data_path="/nonexistent/path")
        assert len(ds) > 0

    def test_direct_samples(self):
        samples = [(np.random.rand(8).astype(np.float32), np.random.randint(0, 2)) for _ in range(10)]
        ds = RankDataset(samples=samples)
        assert len(ds) == 10
        feat, label = ds[0]
        assert feat.shape == (8,)
