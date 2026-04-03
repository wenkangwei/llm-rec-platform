"""E2E 测试 — 通过 FastAPI TestClient 验证真实 HTTP 端点"""

from __future__ import annotations

import asyncio

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("fastapi")

import httpx  # noqa: E402

from server.app import create_app


@pytest.fixture
def app():
    """创建 FastAPI 应用实例。"""
    return create_app()


@pytest.fixture
def client(app):
    """httpx 异步测试客户端。"""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestHealthEndpoint:
    """GET /api/health 端点测试。"""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_has_components(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert isinstance(data["components"], dict)


class TestMetricsEndpoint:
    """GET /api/metrics 端点测试。"""

    @pytest.mark.asyncio
    async def test_metrics_returns_text(self, client):
        resp = await client.get("/api/metrics")
        assert resp.status_code == 200
        assert "TYPE" in resp.text or resp.text.strip() in ('', '""')


class TestRecommendEndpoint:
    """POST /api/recommend 端点测试。"""

    @pytest.mark.asyncio
    async def test_recommend_basic(self, client):
        resp = await client.post("/api/recommend", json={
            "user_id": "u1",
            "scene": "home_feed",
            "num": 10,
            "page": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert "items" in data
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_recommend_default_values(self, client):
        resp = await client.post("/api/recommend", json={"user_id": "u1"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_recommend_invalid_num(self, client):
        resp = await client.post("/api/recommend", json={
            "user_id": "u1",
            "num": 0,  # must be >= 1
        })
        assert resp.status_code == 422


class TestSearchEndpoint:
    """POST /api/search 端点测试。"""

    @pytest.mark.asyncio
    async def test_search_basic(self, client):
        resp = await client.post("/api/search", json={
            "user_id": "u1",
            "query": "python教程",
            "num": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "python教程"
        assert "items" in data
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_search_empty_query_rejected(self, client):
        resp = await client.post("/api/search", json={
            "user_id": "u1",
            "query": "",
        })
        assert resp.status_code == 422


class TestTrackEndpoint:
    """POST /api/track 端点测试。"""

    @pytest.mark.asyncio
    async def test_track_click(self, client):
        resp = await client.post("/api/track", json={
            "user_id": "u1",
            "item_id": "i1",
            "action": "click",
            "scene": "home_feed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_track_with_dwell_time(self, client):
        resp = await client.post("/api/track", json={
            "user_id": "u1",
            "item_id": "i1",
            "action": "dwell",
            "scene": "home_feed",
            "dwell_time_sec": 12.5,
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestChatEndpoint:
    """POST /api/chat 端点测试。"""

    @pytest.mark.asyncio
    async def test_chat_creates_session(self, client):
        resp = await client.post("/api/chat", json={
            "user_id": "admin",
            "message": "你好",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"]
        assert data["reply"]

    @pytest.mark.asyncio
    async def test_chat_with_existing_session(self, client):
        # 先创建会话
        resp1 = await client.post("/api/chat", json={
            "user_id": "admin",
            "message": "你好",
        })
        session_id = resp1.json()["session_id"]

        # 使用同一会话
        resp2 = await client.post("/api/chat", json={
            "session_id": session_id,
            "user_id": "admin",
            "message": "今天延迟多少",
        })
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id


class TestMiddleware:
    """中间件测试。"""

    @pytest.mark.asyncio
    async def test_request_id_header(self, client):
        resp = await client.get("/api/health")
        assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        resp = await client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in resp.headers
