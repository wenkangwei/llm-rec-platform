"""protocols 模块单元测试 — RecContext / Converters / Request / Response"""

from __future__ import annotations

import pytest

from protocols.schemas.context import Item, RecContext, StageMetrics
from protocols.schemas.request import RecRequest, SearchRequest, TrackEvent
from protocols.schemas.response import HealthResponse, RecItem, RecResponse, SearchResponse
from protocols.schemas.converters import (
    community_to_context,
    context_to_response,
    context_to_search_response,
    follow_to_context,
    request_to_context,
    search_to_context,
)


class TestRecContext:
    """RecContext 数据结构测试。"""

    def test_create(self):
        ctx = RecContext(request_id="r1", user_id="u1", scene="home_feed")
        assert ctx.request_id == "r1"
        assert ctx.candidates == []
        assert ctx.page == 0

    def test_with_candidates(self):
        items = [Item(id="i1", score=0.9, source="hot"), Item(id="i2", score=0.8, source="cf")]
        ctx = RecContext(request_id="r1", user_id="u1", scene="home_feed", candidates=items)
        assert len(ctx.candidates) == 2

    def test_stage_metrics(self):
        m = StageMetrics(stage_name="recall", latency_ms=10.5, input_count=0, output_count=500)
        assert m.stage_name == "recall"
        assert m.latency_ms == 10.5


class TestItem:
    """Item 数据结构测试。"""

    def test_defaults(self):
        item = Item(id="i1")
        assert item.score == 0.0
        assert item.source == ""
        assert item.features == {}

    def test_full(self):
        item = Item(id="i1", score=0.95, source="hot", features={"author_id": "a1"})
        assert item.score == 0.95
        assert item.features["author_id"] == "a1"


class TestRequestSchemas:
    """HTTP 请求 Schema 测试。"""

    def test_rec_request_defaults(self):
        req = RecRequest(user_id="u1")
        assert req.scene == "home_feed"
        assert req.page == 0
        assert req.num == 20

    def test_rec_request_custom(self):
        req = RecRequest(user_id="u1", scene="search_feed", num=50, page=2)
        assert req.num == 50

    def test_search_request(self):
        req = SearchRequest(user_id="u1", query="python")
        assert req.query == "python"

    def test_search_request_empty_query_fails(self):
        with pytest.raises(Exception):
            SearchRequest(user_id="u1", query="")

    def test_track_event(self):
        evt = TrackEvent(user_id="u1", item_id="i1", action="click")
        assert evt.action == "click"
        assert evt.dwell_time_sec is None


class TestResponseSchemas:
    """HTTP 响应 Schema 测试。"""

    def test_rec_response(self):
        resp = RecResponse(request_id="r1", items=[])
        assert resp.total == 0
        assert not resp.has_more

    def test_health_response(self):
        resp = HealthResponse()
        assert resp.status == "ok"


class TestConverters:
    """协议转换器测试。"""

    def test_request_to_context(self):
        req = RecRequest(user_id="u1", scene="home_feed", num=30, page=1)
        ctx = request_to_context(req, "req_123")
        assert ctx.request_id == "req_123"
        assert ctx.user_id == "u1"
        assert ctx.scene == "home_feed"
        assert ctx.page_size == 30

    def test_search_to_context(self):
        req = SearchRequest(user_id="u1", query="test query")
        ctx = search_to_context(req, "req_456")
        assert ctx.scene == "search_feed"
        assert ctx.query == "test query"

    def test_context_to_response(self):
        ctx = RecContext(
            request_id="r1",
            user_id="u1",
            scene="home_feed",
            page_size=20,
            candidates=[
                Item(id="i1", score=0.95, source="hot", metadata={"summary": "test"}),
                Item(id="i2", score=0.80, source="cf"),
            ],
        )
        resp = context_to_response(ctx)
        assert resp.request_id == "r1"
        assert len(resp.items) == 2
        assert resp.items[0].item_id == "i1"
        assert resp.items[0].score == 0.95
        assert resp.items[0].summary == "test"
        assert resp.total == 2

    def test_context_to_response_pagination(self):
        items = [Item(id=f"i{i}", score=1.0 - i * 0.01) for i in range(50)]
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            page_size=20, page=0, candidates=items,
        )
        resp = context_to_response(ctx)
        assert len(resp.items) == 20
        assert resp.has_more is True
        assert resp.total == 50

    def test_context_to_search_response(self):
        ctx = RecContext(
            request_id="r1", user_id="u1", scene="search_feed",
            query="test", page_size=20,
            candidates=[Item(id="i1", score=0.9)],
        )
        resp = context_to_search_response(ctx)
        assert resp.query == "test"
        assert len(resp.items) == 1

    def test_follow_to_context(self):
        from protocols.schemas.request import FollowFeedRequest

        req = FollowFeedRequest(user_id="u1", num=15)
        ctx = follow_to_context(req, "req_789")
        assert ctx.scene == "follow_feed"
        assert ctx.page_size == 15

    def test_community_to_context(self):
        from protocols.schemas.request import CommunityFeedRequest

        req = CommunityFeedRequest(user_id="u1", community_id="c1")
        ctx = community_to_context(req, "req_000")
        assert ctx.scene == "community_feed"
        assert ctx.extras["community_id"] == "c1"
