"""首页信息流场景入口"""

from __future__ import annotations

from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("scene.home_feed")


class HomeFeedScene:
    """首页信息流推荐场景。

    完整链路：召回 → 粗排 → 精排 → 重排 → 混排
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
        """执行首页推荐。"""
        ctx = create_context(
            user_id=user_id,
            scene="home_feed",
            page=page,
            page_size=page_size,
        )
        if user_features:
            ctx.user_features = user_features

        ctx = await self._executor.execute(ctx)
        logger.info(f"首页推荐完成", user_id=user_id, items=len(ctx.candidates))
        return ctx
