"""HTTP 请求 Schema — 仅负责接口入参校验。

与内部 RecContext 解耦，转换逻辑见 protocols.schemas.converters。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RecRequest(BaseModel):
    """首页推荐请求。"""
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


class FollowFeedRequest(BaseModel):
    """关注动态请求。"""
    user_id: str
    page: int = Field(default=0, ge=0)
    num: int = Field(default=20, ge=1, le=100)


class CommunityFeedRequest(BaseModel):
    """社区推荐请求。"""
    user_id: str
    community_id: Optional[str] = None
    page: int = Field(default=0, ge=0)
    num: int = Field(default=20, ge=1, le=100)


class TrackEvent(BaseModel):
    """用户行为上报。"""
    user_id: str
    item_id: str
    action: str  # click, like, share, comment, dwell, expose
    scene: str = ""
    request_id: str = ""
    dwell_time_sec: Optional[float] = None
    extra: Optional[dict[str, Any]] = None
