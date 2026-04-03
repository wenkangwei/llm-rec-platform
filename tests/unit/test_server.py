"""server 模块单元测试 — FastAPI 应用 / 路由"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from httpx import AsyncClient, ASGITransport

from server.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthRoute:
    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        response = await client.get("/api/metrics")
        assert response.status_code == 200


class TestRecommendRoute:
    @pytest.mark.asyncio
    async def test_recommend(self, client):
        response = await client.post(
            "/api/recommend",
            json={"user_id": "u1", "scene": "home_feed", "num": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_recommend_missing_user(self, client):
        response = await client.post("/api/recommend", json={"scene": "home_feed"})
        assert response.status_code == 422  # Validation error


class TestSearchRoute:
    @pytest.mark.asyncio
    async def test_search(self, client):
        response = await client.post(
            "/api/search",
            json={"user_id": "u1", "query": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["query"] == "test"


class TestTrackRoute:
    @pytest.mark.asyncio
    async def test_track(self, client):
        response = await client.post(
            "/api/track",
            json={"user_id": "u1", "item_id": "i1", "action": "click"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMiddleware:
    @pytest.mark.asyncio
    async def test_request_id_header(self, client):
        response = await client.get("/api/health")
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers
