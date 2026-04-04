"""LLM 后端管理路由 — 查看状态、手动切换 provider"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status")
async def llm_status(request: Request):
    """查看所有 LLM provider 的健康状态和当前活跃 provider。"""
    llm_backend = getattr(request.app.state, "llm_backend", None)
    if llm_backend is None:
        return {"active": "none", "providers": [], "error": "LLM backend not initialized"}

    # 如果是 LLMRouter，返回详细状态
    if hasattr(llm_backend, "get_status"):
        return llm_backend.get_status()

    # 单后端模式
    healthy = await llm_backend.health_check()
    return {
        "active": "default",
        "providers": [{"name": "default", "priority": 1, "available": healthy}],
    }


@router.post("/select/{name}")
async def select_provider(name: str, request: Request):
    """手动切换到指定 LLM provider。"""
    llm_backend = getattr(request.app.state, "llm_backend", None)
    if llm_backend is None:
        return {"error": "LLM backend not initialized"}

    if hasattr(llm_backend, "select_provider"):
        ok = llm_backend.select_provider(name)
        if ok:
            return {"success": True, "active": name}
        return {"success": False, "error": f"provider {name} 不可用或不存在"}
    return {"error": "当前后端不支持 provider 切换（非路由模式）"}
