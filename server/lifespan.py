"""生命周期管理 — 应用启动/关闭时的资源初始化和清理"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from configs.settings import get_settings
from experiment.manager import ExperimentManager
from experiment.models import Experiment, ExperimentVariant
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

    # 初始化 LLM 后端（多 provider 路由 + 自动降级）
    try:
        llm_config = settings.raw.get("llm", {})
        providers = llm_config.get("providers", [])

        if providers:
            # 新配置：多 provider 路由
            llm_backend = LLMFactory.create_router(llm_config)
        else:
            # 兼容旧配置：单 backend
            backend_cfg = llm_config.get("backend", {})
            llm_backend = LLMFactory.create(backend_cfg)

        await llm_backend.warmup()
        app.state.llm_backend = llm_backend
        app.state.components_health["llm"] = True
        logger.info("LLM 后端初始化完成")
    except Exception as e:
        logger.error("LLM 后端初始化失败，降级到 Mock", error=str(e))
        from llm.backends.mock_backend import MockBackend
        llm_backend = MockBackend()
        await llm_backend.warmup()
        app.state.llm_backend = llm_backend
        app.state.components_health["llm"] = True

    # 初始化 ExperimentManager（在 Pipeline 之前，因为 Pipeline 需要引用）
    try:
        exp_manager = ExperimentManager()
        exp_configs = settings.raw.get("experiment", {}).get("experiments", [])
        for exp_cfg in exp_configs:
            if not exp_cfg.get("enabled", True):
                continue
            variants = [
                ExperimentVariant(
                    name=v["name"],
                    traffic_percent=v.get("traffic_percent", 50.0),
                    config=v.get("config", {}),
                )
                for v in exp_cfg.get("variants", [])
            ]
            exp = Experiment(
                id=exp_cfg["id"],
                name=exp_cfg.get("name", exp_cfg["id"]),
                variants=variants,
            )
            exp_manager.create_experiment(exp)
            exp_manager.start_experiment(exp.id)
            logger.info(f"实验加载并启动: {exp.id}")
        app.state.experiment_manager = exp_manager
        app.state.components_health["experiment"] = True
        logger.info("ExperimentManager 初始化完成", experiments=len(exp_manager._experiments))
    except Exception as e:
        logger.error("ExperimentManager 初始化失败", error=str(e))
        app.state.experiment_manager = None
        app.state.components_health["experiment"] = False

    # 初始化 PipelineExecutor
    try:
        exp_mgr = getattr(app.state, "experiment_manager", None)
        executor = PipelineExecutor(experiment_manager=exp_mgr)
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
            chat_manager = ChatSessionManager(app.state.llm_backend, pipeline_state, mysql_store=None)
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

    # 初始化存储连接（连接失败不崩溃，graceful degradation）
    storage_config = settings.validated.storage

    # Redis
    try:
        from storage.redis import RedisStore, set_redis
        redis_conf = storage_config.redis
        redis_store = RedisStore(
            host=redis_conf.host, port=redis_conf.port, db=redis_conf.db,
            password=redis_conf.password, pool_size=redis_conf.pool_size,
        )
        await redis_store.connect()
        app.state.redis = redis_store

        # 同步 Redis 客户端（召回模块需要 zrevrange 等同步操作）
        import redis as sync_redis
        sync_client = sync_redis.Redis(
            host=redis_conf.host, port=redis_conf.port, db=redis_conf.db,
            password=redis_conf.password, decode_responses=True,
        )
        sync_client.ping()
        set_redis(sync_client)

        app.state.components_health["redis"] = True
        logger.info("Redis 连接完成")
    except Exception as e:
        logger.warning("Redis 连接失败，使用降级模式", error=str(e))
        app.state.redis = None
        app.state.components_health["redis"] = False

    # MySQL
    try:
        from storage.mysql import MySQLStore
        mysql_conf = storage_config.mysql
        mysql_store = MySQLStore(
            host=mysql_conf.host, port=mysql_conf.port,
            user=mysql_conf.user, password=mysql_conf.password,
            database=mysql_conf.database, pool_size=mysql_conf.pool_size,
        )
        await mysql_store.connect()
        app.state.mysql = mysql_store
        app.state.components_health["mysql"] = True
        # 注入 MySQL store 到 ChatManager 的 DBQueryTool
        # 注入 PipelineExecutor 到 RecommendTestTool
        if getattr(app.state, "chat_manager", None):
            for tool in app.state.chat_manager._tools:
                if hasattr(tool, "_mysql"):
                    tool._mysql = mysql_store
                if hasattr(tool, "_executor"):
                    tool._executor = getattr(app.state, "pipeline_executor", None)
        logger.info("MySQL 连接完成")
    except Exception as e:
        logger.warning("MySQL 连接失败，使用降级模式", error=str(e))
        app.state.mysql = None
        app.state.components_health["mysql"] = False

    # ClickHouse
    try:
        from storage.clickhouse import ClickHouseStore
        ch_conf = storage_config.clickhouse
        ch_store = ClickHouseStore(
            host=ch_conf.host, port=ch_conf.port,
            user=ch_conf.user, password=ch_conf.password,
            database=ch_conf.database,
        )
        await ch_store.async_connect()
        app.state.clickhouse = ch_store
        app.state.components_health["clickhouse"] = True
        logger.info("ClickHouse 连接完成")
    except Exception as e:
        logger.warning("ClickHouse 连接失败，使用降级模式", error=str(e))
        app.state.clickhouse = None
        app.state.components_health["clickhouse"] = False

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
    if app.state.clickhouse:
        await app.state.clickhouse.async_close()

    # 卸载模型
    if app.state.model_manager:
        app.state.model_manager.shutdown_all()

    # 关闭 LLM 后端
    if app.state.llm_backend and hasattr(app.state.llm_backend, "shutdown"):
        await app.state.llm_backend.shutdown()

    logger.info("服务已关闭")
