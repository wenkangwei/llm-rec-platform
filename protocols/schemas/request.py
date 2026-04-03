"""推荐请求 Schema — HTTP 接口入参"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RecRequest(BaseModel):
    """推荐请求。"""
    user_id: str
    scene: str = "home_feed"
    page: int = Field(default=0, ge=0)
    num: int = Field(default=20, ge=1, le=100)
    context: Optional[dict[str, Any]] = None


class SearchRequest(BaseModel):
    """搜索推荐请求。"""
    user_id: str
    query: str = Field(min_length=1, max_length=200)
    page: int = Field(default=0, ge=0)
    num: int = Field(default=20, ge=1, le=100)
    context: Optional[dict[str, Any]] = None


class TrackEvent(BaseModel):
    """用户行为上报。"""
    user_id: str
    item_id: str
    action: str  # click, like, share, comment, dwell, expose
    scene: str = ""
    request_id: str = ""
    dwell_time_sec: Optional[float] = None
    extra: Optional[dict[str, Any]] = None
