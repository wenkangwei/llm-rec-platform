"""推荐请求路由 — HTTP Request → RecContext → Pipeline → RecResponse"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.converters import (
    context_to_response,
    request_to_context,
)
from protocols.schemas.request import RecRequest
from protocols.schemas.response import RecResponse

router = APIRouter()


@router.post("/recommend", response_model=RecResponse)
async def recommend(req: RecRequest, request: Request) -> RecResponse:
    """推荐接口 — 首页/关注/社区等场景。

    流程:
    1. HTTP Request → request_to_context() → RecContext（协议层转换）
    2. RecContext → PipelineExecutor.execute()（function call，初版不走 gRPC）
    3. RecContext → context_to_response() → HTTP Response（协议层转换）
    """
    request_id = getattr(request.state, "request_id", "")

    # 1. HTTP → RecContext
    ctx = request_to_context(req, request_id)

    # 2. Pipeline 执行（function call，初版不走 gRPC）
    executor = getattr(request.app.state, "pipeline_executor", None)
    if executor:
        ctx = await executor.execute(ctx)

    # 3. RecContext → HTTP Response
    return context_to_response(ctx)
