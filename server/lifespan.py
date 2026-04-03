"""生命周期管理 — 应用启动/关闭时的资源初始化和清理"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from configs.settings import get_settings
from utils.logger import get_struct_logger

logger = get_struct_logger("lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI 生命周期管理：startup → yield → shutdown。"""
    # ===== Startup =====
    settings = get_settings()
    logger.info("服务启动中...", host=settings.server.host, port=settings.server.port)

    # 初始化配置
    app.state.settings = settings
    app.state.components_health = {}

    # 存储连接（后续 Phase 实现）
    app.state.redis = None
    app.state.mysql = None
    app.state.clickhouse = None

    # 模型管理器（后续 Phase 实现）
    app.state.model_manager = None

    # LLM 后端（后续 Phase 实现）
    app.state.llm_backend = None

    app.state.components_health["config"] = True
    logger.info("服务启动完成")

    yield

    # ===== Shutdown =====
    logger.info("服务关闭中...")

    # 关闭存储连接
    if app.state.redis:
        await app.state.redis.close()
    if app.state.mysql:
        await app.state.mysql.close()

    # 卸载模型
    if app.state.model_manager:
        app.state.model_manager.shutdown_all()

    # 关闭 LLM 后端
    if app.state.llm_backend:
        await app.state.llm_backend.shutdown()

    logger.info("服务已关闭")
