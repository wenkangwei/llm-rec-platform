"""全局异常处理中间件"""

from __future__ import annotations

import traceback

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from utils.logger import get_struct_logger

logger = get_struct_logger("error_handler")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """捕获未处理异常，返回统一错误响应。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "-")
            logger.error(
                f"未处理异常: {exc}",
                request_id=request_id,
                path=request.url.path,
                traceback=traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )
