"""认证中间件 — API Key 校验"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# 不需要认证的路径前缀
_PUBLIC_PATHS = ("/api/health", "/docs", "/openapi", "/redoc")


class AuthMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件（预留，默认放行）。"""

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 健康检查和文档路径跳过认证
        if any(request.url.path.startswith(p) for p in _PUBLIC_PATHS):
            return await call_next(request)

        # 未配置 API Key 时跳过认证
        if not self._api_key:
            return await call_next(request)

        # 校验 API Key
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != self._api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        return await call_next(request)
