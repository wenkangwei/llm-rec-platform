"""社区/话题推荐场景入口"""

from __future__ import annotations

from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("scene.community_feed")


class CommunityFeedScene:
    """社区/话题推荐场景。

    基于用户兴趣和社交关系的社区内容推荐。
    """

    def __init__(self, executor: PipelineExecutor):
        self._executor = executor

    async def recommend(
        self,
        user_id: str,
        community_id: str | None = None,
        page: int = 0,
        page_size: int = 20,
        user_features: dict | None = None,
    ) -> RecContext:
        ctx = create_context(
            user_id=user_id,
            scene="community_feed",
            page=page,
            page_size=page_size,
        )
        if user_features:
            ctx.user_features = user_features
        if community_id:
            ctx.extras["community_id"] = community_id

        ctx = await self._executor.execute(ctx)
        logger.info(f"社区推荐完成", user_id=user_id, items=len(ctx.candidates))
        return ctx
