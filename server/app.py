"""FastAPI 应用工厂"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs.settings import get_settings
from server.lifespan import lifespan
from server.middleware.error_handler import ErrorHandlerMiddleware
from server.middleware.logging import LoggingMiddleware
from server.middleware.rate_limit import RateLimitMiddleware
from server.middleware.request_id import RequestIDMiddleware


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    settings = get_settings()

    app = FastAPI(
        title="LLM Rec Platform",
        description="融合 LLM 的智能推荐系统平台",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 自定义中间件（执行顺序：从外到内，最后添加的最先执行）
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_sec=60)
    app.add_middleware(RequestIDMiddleware)

    # 注册路由
    _register_routes(app)

    return app


def _register_routes(app: FastAPI) -> None:
    """注册所有路由模块。"""
    from server.routes import chat, experiment, health, llm, recommend, search, social, track, webui

    app.include_router(webui.router)
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(recommend.router, prefix="/api", tags=["recommend"])
    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(track.router, prefix="/api", tags=["track"])
    app.include_router(social.router, prefix="/api", tags=["social"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(experiment.router, tags=["experiment"])
    app.include_router(llm.router, tags=["llm"])
