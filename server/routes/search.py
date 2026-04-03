"""搜索推荐路由"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.request import SearchRequest
from protocols.schemas.response import SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    """搜索推荐接口 — 基于 query 的个性化搜索结果排序。

    当前为骨架实现。后续 Phase 接入搜索链路 + LLM 摘要。
    """
    # TODO: Phase 2/4 接入搜索链路 + LLM 搜索重排摘要
    return SearchResponse(
        request_id=getattr(request.state, "request_id", ""),
        query=req.query,
        items=[],
        total=0,
    )
