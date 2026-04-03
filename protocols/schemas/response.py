"""HTTP 响应 Schema — 仅负责接口出参格式化。

与内部 RecContext 解耦，转换逻辑见 protocols.schemas.converters。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class RecItem(BaseModel):
    """推荐结果中的单个物品。"""
    item_id: str
    score: float = 0.0
    source: str = ""
    summary: Optional[str] = None  # LLM 生成的摘要
    extra: Optional[dict[str, Any]] = None


class RecResponse(BaseModel):
    """推荐响应。"""
    request_id: str
    items: list[RecItem]
    trace_id: Optional[str] = None
    total: int = 0
    page: int = 0
    has_more: bool = False


class SearchResponse(BaseModel):
    """搜索推荐响应。"""
    request_id: str
    query: str
    items: list[RecItem]
    trace_id: Optional[str] = None
    total: int = 0
    summary: Optional[str] = None


class TrackResponse(BaseModel):
    """行为上报响应。"""
    success: bool
    message: str = ""


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str = "ok"
    version: str = "0.1.0"
    components: dict[str, bool] = {}
