"""生命周期管理 — 应用启动/关闭时的资源初始化和清理"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from configs.settings import get_settings
from llm.factory import LLMFactory
from pipeline.executor import PipelineExecutor
from utils.logger import get_struct_logger

logger = get_struct_logger("lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI 生命周期管理：startup → yield → shutdown。"""
    # ===== Startup =====
    settings = get_settings()
    logger.info("服务启动中...", host=settings.server.host, port=settings.server.port)

    app.state.settings = settings
    app.state.components_health = {}

    # 初始化 LLM 后端
    try:
        llm_config = settings.raw.get("llm", {}).get("backend", {})
        # 开发环境默认使用 mock
        import os
        env = os.environ.get("APP_ENV", "development")
        if env == "development":
            from llm.backends.mock_backend import MockBackend
            llm_backend = MockBackend()
        else:
            llm_backend = LLMFactory.create(llm_config)
        await llm_backend.warmup()
        app.state.llm_backend = llm_backend
        app.state.components_health["llm"] = True
        logger.info("LLM 后端初始化完成")
    except Exception as e:
        logger.error("LLM 后端初始化失败", error=str(e))
        app.state.llm_backend = None
        app.state.components_health["llm"] = False

    # 初始化 PipelineExecutor
    try:
        executor = PipelineExecutor()
        pipeline_config = settings.raw.get("pipeline", {})
        stage_configs = pipeline_config.get("stages", [])
        if stage_configs:
            executor.load_from_config(stage_configs)
        await executor.warmup_all()
        app.state.pipeline_executor = executor
        app.state.components_health["pipeline"] = True
        logger.info("Pipeline 初始化完成", stages=len(executor._stages))
    except Exception as e:
        logger.error("Pipeline 初始化失败", error=str(e))
        app.state.pipeline_executor = None
        app.state.components_health["pipeline"] = False

    # 初始化 ChatManager
    try:
        if app.state.llm_backend:
            from llm.chat.manager import ChatSessionManager
            pipeline_state = {
                "channels": settings.raw.get("pipeline", {}).get("recall", {}).get("channels", {}),
            }
            chat_manager = ChatSessionManager(app.state.llm_backend, pipeline_state)
            app.state.chat_manager = chat_manager
            app.state.components_health["chat"] = True
            logger.info("ChatManager 初始化完成")
        else:
            app.state.chat_manager = None
            app.state.components_health["chat"] = False
    except Exception as e:
        logger.error("ChatManager 初始化失败", error=str(e))
        app.state.chat_manager = None
        app.state.components_health["chat"] = False

    # 存储连接（需要实际服务时启用）
    app.state.redis = None
    app.state.mysql = None
    app.state.clickhouse = None
    app.state.model_manager = None

    app.state.components_health["config"] = True
    logger.info("服务启动完成")

    yield

    # ===== Shutdown =====
    logger.info("服务关闭中...")

    # 关闭 Pipeline
    if app.state.pipeline_executor:
        await app.state.pipeline_executor.shutdown_all()

    # 关闭存储连接
    if app.state.redis:
        await app.state.redis.close()
    if app.state.mysql:
        await app.state.mysql.close()

    # 卸载模型
    if app.state.model_manager:
        app.state.model_manager.shutdown_all()

    # 关闭 LLM 后端
    if app.state.llm_backend and hasattr(app.state.llm_backend, "shutdown"):
        await app.state.llm_backend.shutdown()

    logger.info("服务已关闭")
