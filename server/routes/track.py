"""用户行为上报路由"""

from __future__ import annotations

from fastapi import APIRouter

from protocols.schemas.request import TrackEvent
from protocols.schemas.response import TrackResponse

router = APIRouter()


@router.post("/track", response_model=TrackResponse)
async def track(event: TrackEvent) -> TrackResponse:
    """用户行为上报 — 点击、点赞、分享、评论、停留时长等。

    当前为骨架实现，后续 Phase 接入日志落盘 + 训练标签回填。
    """
    # TODO: Phase 5 接入异步日志落盘
    return TrackResponse(success=True, message="tracked")
