"""推荐请求路由"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.request import RecRequest
from protocols.schemas.response import RecResponse

router = APIRouter()


@router.post("/recommend", response_model=RecResponse)
async def recommend(req: RecRequest, request: Request) -> RecResponse:
    """推荐接口 — 根据用户ID和场景返回个性化推荐结果。

    当前为骨架实现，返回空结果。后续 Phase 接入完整链路。
    """
    # TODO: Phase 2 接入 pipeline executor
    return RecResponse(
        request_id=getattr(request.state, "request_id", ""),
        items=[],
        total=0,
        page=req.page,
        has_more=False,
    )
