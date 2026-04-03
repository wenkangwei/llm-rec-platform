"""用户行为上报路由"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Request

from protocols.schemas.request import TrackEvent
from protocols.schemas.response import TrackResponse
from utils.logger import get_struct_logger

logger = get_struct_logger("routes.track")

router = APIRouter()


@router.post("/track", response_model=TrackResponse)
async def track(event: TrackEvent, request: Request) -> TrackResponse:
    """用户行为上报 — 点击、点赞、分享、评论、停留时长等。

    流程:
    1. 异步写入实时日志
    2. 延迟回填训练标签（通过 TrainingLogger.backfill_labels）
    """
    logger.info(
        f"行为上报",
        user_id=event.user_id,
        item_id=event.item_id,
        action=event.action,
        scene=event.scene,
    )

    # 异步落盘（不阻塞响应）
    training_logger = getattr(request.app.state, "training_logger", None)
    if training_logger:
        asyncio.create_task(training_logger.backfill_labels(
            request_id=event.request_id,
            item_id=event.item_id,
            labels={
                "action": event.action,
                "scene": event.scene,
                "dwell_time_sec": event.dwell_time_sec,
                "timestamp": time.time(),
            },
        ))

    return TrackResponse(success=True, message="tracked")
