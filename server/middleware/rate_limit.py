"""限流中间间 — 基于内存的滑动窗口限流"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的内存限流中间件。生产环境应替换为 Redis 限流。"""

    def __init__(self, app, max_requests: int = 100, window_sec: int = 60):
        super().__init__(app)
        self._max_requests = max_requests
        self._window_sec = window_sec
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 清理过期记录
        self._requests[client_ip] = [
            t for t in self._requests[client_ip]
            if now - t < self._window_sec
        ]

        if len(self._requests[client_ip]) >= self._max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
