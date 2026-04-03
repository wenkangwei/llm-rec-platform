"""请求日志中间件 — 记录请求方法、路径、耗时"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from utils.logger import get_struct_logger

logger = get_struct_logger("http")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path}",
            request_id=request_id,
            status=response.status_code,
            elapsed_ms=f"{elapsed_ms:.1f}",
        )

        response.headers["X-Elapsed-Ms"] = f"{elapsed_ms:.1f}"
        return response
