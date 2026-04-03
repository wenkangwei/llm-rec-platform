"""关注动态流场景入口"""

from __future__ import annotations

from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("scene.follow_feed")


class FollowFeedScene:
    """关注动态流场景。

    聚合已关注用户/社区的内容，按时间/兴趣排序。
    """

    def __init__(self, executor: PipelineExecutor):
        self._executor = executor

    async def recommend(
        self,
        user_id: str,
        page: int = 0,
        page_size: int = 20,
        user_features: dict | None = None,
    ) -> RecContext:
        ctx = create_context(
            user_id=user_id,
            scene="follow_feed",
            page=page,
            page_size=page_size,
        )
        if user_features:
            ctx.user_features = user_features

        ctx = await self._executor.execute(ctx)
        logger.info(f"关注动态推荐完成", user_id=user_id, items=len(ctx.candidates))
        return ctx
