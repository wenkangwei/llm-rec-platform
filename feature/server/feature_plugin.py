"""特征插件 — PipelineStage 集成"""

from __future__ import annotations

from pipeline.base import PipelineStage
from feature.server.feature_server import FeatureServer
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.server.plugin")


class FeatureFetchPlugin(PipelineStage):
    """特征拉取 PipelineStage：在链路执行前拉取用户特征。"""

    def __init__(self, feature_server: FeatureServer):
        self._server = feature_server

    def name(self) -> str:
        return "feature_fetch"

    def process(self, ctx: RecContext) -> RecContext:
        """拉取特征并注入到上下文。"""
        # 同步包装（生产环境应用 async）
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 已经在 async 上下文中，创建 task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                user_features = pool.submit(
                    asyncio.run, self._server.fetch_user_features(ctx.user_id, ctx.scene)
                ).result()
        else:
            user_features = asyncio.run(
                self._server.fetch_user_features(ctx.user_id, ctx.scene)
            )

        ctx.user_features = user_features
        return ctx
