"""server 中间件单元测试 — auth / error_handler / logging / rate_limit / request_id"""

from __future__ import annotations

import pytest

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from server.middleware.auth import AuthMiddleware
from server.middleware.error_handler import ErrorHandlerMiddleware
from server.middleware.logging import LoggingMiddleware
from server.middleware.rate_limit import RateLimitMiddleware
from server.middleware.request_id import RequestIDMiddleware


def _make_app(*middlewares) -> FastAPI:
    """创建测试用 FastAPI app，挂载中间件和简单路由。"""
    app = FastAPI()

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/protected")
    async def protected():
        return {"data": "secret"}

    @app.get("/api/error")
    async def error_endpoint():
        raise ValueError("test error")

    @app.post("/api/recommend")
    async def recommend():
        return {"items": []}

    for mw in middlewares:
        app.add_middleware(mw)

    return app


@pytest.fixture
def app_no_auth():
    return _make_app(AuthMiddleware)


@pytest.fixture
def app_with_auth():
    app = FastAPI()

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/protected")
    async def protected():
        return {"data": "secret"}

    app.add_middleware(AuthMiddleware, api_key="test-secret")
    return app


@pytest.fixture
def app_error():
    return _make_app(ErrorHandlerMiddleware)


@pytest.fixture
def app_logging():
    return _make_app(LoggingMiddleware)


@pytest.fixture
def app_rate_limit():
    app = FastAPI()

    @app.get("/api/test")
    async def test_route():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, max_requests=3, window_sec=60)
    return app


@pytest.fixture
def app_request_id():
    return _make_app(RequestIDMiddleware)


# ===== AuthMiddleware =====

class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_no_api_key_configured(self, app_no_auth):
        async with AsyncClient(transport=ASGITransport(app=app_no_auth), base_url="http://test") as c:
            r = await c.get("/api/protected")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_public_path_skips_auth(self, app_with_auth):
        async with AsyncClient(transport=ASGITransport(app=app_with_auth), base_url="http://test") as c:
            r = await c.get("/api/health")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_no_key_rejected(self, app_with_auth):
        async with AsyncClient(transport=ASGITransport(app=app_with_auth), base_url="http://test") as c:
            r = await c.get("/api/protected")
            assert r.status_code == 401
            assert r.json()["detail"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_protected_valid_header(self, app_with_auth):
        async with AsyncClient(transport=ASGITransport(app=app_with_auth), base_url="http://test") as c:
            r = await c.get("/api/protected", headers={"X-API-Key": "test-secret"})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_valid_query_param(self, app_with_auth):
        async with AsyncClient(transport=ASGITransport(app=app_with_auth), base_url="http://test") as c:
            r = await c.get("/api/protected?api_key=test-secret")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_wrong_key(self, app_with_auth):
        async with AsyncClient(transport=ASGITransport(app=app_with_auth), base_url="http://test") as c:
            r = await c.get("/api/protected", headers={"X-API-Key": "wrong"})
            assert r.status_code == 401


# ===== ErrorHandlerMiddleware =====

class TestErrorHandlerMiddleware:
    @pytest.mark.asyncio
    async def test_normal_request(self, app_error):
        async with AsyncClient(transport=ASGITransport(app=app_error), base_url="http://test") as c:
            r = await c.get("/api/health")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_exception_returns_500(self, app_error):
        async with AsyncClient(transport=ASGITransport(app=app_error), base_url="http://test") as c:
            r = await c.get("/api/error")
            assert r.status_code == 500
            data = r.json()
            assert data["detail"] == "Internal server error"
            assert "request_id" in data


# ===== LoggingMiddleware =====

class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_adds_elapsed_header(self, app_logging):
        async with AsyncClient(transport=ASGITransport(app=app_logging), base_url="http://test") as c:
            r = await c.get("/api/health")
            assert r.status_code == 200
            assert "X-Elapsed-Ms" in r.headers


# ===== RateLimitMiddleware =====

class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_under_limit_passes(self, app_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_rate_limit), base_url="http://test") as c:
            r = await c.get("/api/test")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_over_limit_rejected(self, app_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_rate_limit), base_url="http://test") as c:
            # Send 3 requests (limit)
            for _ in range(3):
                await c.get("/api/test")
            # 4th should be rejected
            r = await c.get("/api/test")
            assert r.status_code == 429
            assert r.json()["detail"] == "Too many requests"


# ===== RequestIDMiddleware =====

class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_generates_request_id(self, app_request_id):
        async with AsyncClient(transport=ASGITransport(app=app_request_id), base_url="http://test") as c:
            r = await c.get("/api/health")
            assert "X-Request-ID" in r.headers
            assert len(r.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self, app_request_id):
        async with AsyncClient(transport=ASGITransport(app=app_request_id), base_url="http://test") as c:
            r = await c.get("/api/health", headers={"X-Request-ID": "my-id-123"})
            assert r.headers["X-Request-ID"] == "my-id-123"

    @pytest.mark.asyncio
    async def test_different_requests_get_different_ids(self, app_request_id):
        async with AsyncClient(transport=ASGITransport(app=app_request_id), base_url="http://test") as c:
            r1 = await c.get("/api/health")
            r2 = await c.get("/api/health")
            assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
