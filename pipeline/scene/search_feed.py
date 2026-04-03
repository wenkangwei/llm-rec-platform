"""搜索推荐场景入口"""

from __future__ import annotations

from pipeline.context import create_context
from pipeline.executor import PipelineExecutor
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("scene.search_feed")


class SearchFeedScene:
    """搜索推荐场景。

    搜索 query → 召回 → 排序 → LLM 搜索摘要
    """

    def __init__(self, executor: PipelineExecutor):
        self._executor = executor

    async def search(
        self,
        user_id: str,
        query: str,
        page: int = 0,
        page_size: int = 20,
        user_features: dict | None = None,
    ) -> RecContext:
        """执行搜索推荐。"""
        ctx = create_context(
            user_id=user_id,
            scene="search_feed",
            page=page,
            page_size=page_size,
            query=query,
        )
        if user_features:
            ctx.user_features = user_features

        ctx = await self._executor.execute(ctx)

        # LLM 搜索摘要（可选，需配置 llm_backend）
        if hasattr(self, "_llm_backend") and self._llm_backend and ctx.candidates:
            try:
                summary = await self._llm_backend.generate(
                    f"为以下搜索结果生成简短摘要（50字以内）：query={query}，"
                    f"结果数={len(ctx.candidates)}，"
                    f"前3条={', '.join(c.id for c in ctx.candidates[:3])}"
                )
                ctx.extras["search_summary"] = summary
            except Exception as e:
                logger.warning(f"LLM 摘要生成失败", error=str(e))

        logger.info(f"搜索推荐完成", user_id=user_id, query=query, items=len(ctx.candidates))
        return ctx
