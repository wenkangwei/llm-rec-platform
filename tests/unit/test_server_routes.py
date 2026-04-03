"""server 路由单元测试 — health / recommend / search / track / social / chat"""

from __future__ import annotations

import pytest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from server.routes import health, recommend, search, track, social, chat
from server.middleware.error_handler import ErrorHandlerMiddleware
from server.middleware.request_id import RequestIDMiddleware


def _make_app_with_routes() -> FastAPI:
    """创建不触发 lifespan 的测试 app。"""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health.router, prefix="/api")
    app.include_router(recommend.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(track.router, prefix="/api")
    app.include_router(social.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    return app


@pytest.fixture
def app():
    return _make_app_with_routes()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ===== Health Routes =====

class TestHealthRoute:
    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        # Without executor/storage, status depends on default components
        assert data["status"] in ("ok", "degraded")
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_with_executor(self, app, client):
        mock_executor = MagicMock()
        mock_executor.health_check.return_value = {"recall": True, "rank": True}
        app.state.pipeline_executor = mock_executor
        app.state.redis_connected = True
        app.state.mysql_connected = False

        r = await client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "degraded"  # mysql=False
        assert data["components"]["redis"] is True
        assert data["components"]["mysql"] is False

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        r = await client.get("/api/metrics")
        assert r.status_code == 200


# ===== Recommend Route =====

class TestRecommendRoute:
    @pytest.mark.asyncio
    async def test_recommend(self, client):
        r = await client.post(
            "/api/recommend",
            json={"user_id": "u1", "scene": "home_feed", "num": 10},
        )
        assert r.status_code == 200
        data = r.json()
        assert "request_id" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_recommend_missing_user(self, client):
        r = await client.post("/api/recommend", json={"scene": "home_feed"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_recommend_with_executor(self, app, client):
        from protocols.schemas.context import RecContext
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = RecContext(
            request_id="r1", user_id="u1", scene="home_feed",
            candidates=[],
        )
        app.state.pipeline_executor = mock_executor

        r = await client.post(
            "/api/recommend",
            json={"user_id": "u1", "scene": "home_feed"},
        )
        assert r.status_code == 200


# ===== Search Route =====

class TestSearchRoute:
    @pytest.mark.asyncio
    async def test_search(self, client):
        r = await client.post(
            "/api/search",
            json={"user_id": "u1", "query": "Python教程"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["query"] == "Python教程"

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client):
        r = await client.post("/api/search", json={"user_id": "u1"})
        assert r.status_code == 422


# ===== Track Route =====

class TestTrackRoute:
    @pytest.mark.asyncio
    async def test_track(self, client):
        r = await client.post(
            "/api/track",
            json={
                "user_id": "u1",
                "item_id": "i1",
                "action": "click",
                "scene": "home",
                "request_id": "r1",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["message"] == "tracked"

    @pytest.mark.asyncio
    async def test_track_missing_fields(self, client):
        r = await client.post("/api/track", json={"user_id": "u1"})
        assert r.status_code == 422


# ===== Social Routes =====

class TestSocialRoute:
    @pytest.mark.asyncio
    async def test_get_social_graph(self, client):
        r = await client.get("/api/social/u1")
        assert r.status_code == 200
        data = r.json()
        assert data["following"] == []
        assert data["followers"] == []

    @pytest.mark.asyncio
    async def test_follow_user(self, client):
        r = await client.post(
            "/api/social/follow",
            json={"user_id": "u1", "target_user_id": "u2"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


# ===== Chat Routes =====

class TestChatRoute:
    @pytest.mark.asyncio
    async def test_chat_no_manager(self, client):
        r = await client.post(
            "/api/chat",
            json={"message": "hello"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == "error"
        assert "未初始化" in data["reply"]

    @pytest.mark.asyncio
    async def test_chat_with_manager(self, app, client):
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = "s1"
        mock_manager.get_session.return_value = None
        mock_manager.create_session.return_value = mock_session
        mock_manager.chat = AsyncMock(return_value="你好，我是推荐助手")

        app.state.chat_manager = mock_manager

        r = await client.post(
            "/api/chat",
            json={"message": "hello", "user_id": "admin"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == "s1"
        assert data["reply"] == "你好，我是推荐助手"

    @pytest.mark.asyncio
    async def test_chat_stream_no_manager(self, client):
        r = await client.post(
            "/api/chat/stream",
            json={"message": "hello"},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_chat_stream_with_manager(self, app, client):
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = "s1"
        mock_manager.get_session.return_value = None
        mock_manager.create_session.return_value = mock_session
        mock_manager.chat = AsyncMock(return_value="hi")

        app.state.chat_manager = mock_manager

        r = await client.post(
            "/api/chat/stream",
            json={"message": "hello"},
        )
        assert r.status_code == 200
        content = r.text
        assert "session_id" in content
        assert "done" in content
