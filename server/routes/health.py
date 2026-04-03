"""健康检查路由"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """服务健康检查。"""
    components = {}

    # Pipeline 健康检查
    executor = getattr(request.app.state, "pipeline_executor", None)
    if executor:
        components.update(executor.health_check())

    # 存储健康检查
    components["redis"] = getattr(request.app.state, "redis_connected", False)
    components["mysql"] = getattr(request.app.state, "mysql_connected", False)

    all_healthy = all(components.values()) if components else True

    return HealthResponse(
        status="ok" if all_healthy else "degraded",
        version="0.1.0",
        components=components,
    )


@router.get("/metrics")
async def metrics(request: Request) -> str:
    """Prometheus 指标端点。"""
    from monitor.metrics import get_metrics
    m = get_metrics()
    return m.format_prometheus()
