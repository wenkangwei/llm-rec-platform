"""搜索推荐路由 — HTTP Request → RecContext → Pipeline → SearchResponse"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.converters import context_to_search_response, search_to_context
from protocols.schemas.request import SearchRequest
from protocols.schemas.response import SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    """搜索推荐接口。

    流程: HTTP SearchRequest → search_to_context() → PipelineExecutor → context_to_search_response()
    """
    request_id = getattr(request.state, "request_id", "")

    # HTTP → RecContext
    ctx = search_to_context(req, request_id)

    # Pipeline 执行
    executor = getattr(request.app.state, "pipeline_executor", None)
    if executor:
        ctx = await executor.execute(ctx)

    # TODO: Phase 4 — LLM 搜索重排摘要（对 ctx.candidates 生成 summary）

    # RecContext → HTTP Response（含 LLM 摘要）
    resp = context_to_search_response(ctx)
    if ctx.extras.get("search_summary"):
        resp.summary = ctx.extras["search_summary"]
    return resp
