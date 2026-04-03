"""健康检查路由"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """服务健康检查。"""
    components = getattr(request.app.state, "components_health", {})
    all_healthy = all(components.values()) if components else True

    return HealthResponse(
        status="ok" if all_healthy else "degraded",
        version="0.1.0",
        components=components,
    )
