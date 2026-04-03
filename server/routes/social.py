"""社交相关路由"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class FollowRequest(BaseModel):
    user_id: str
    target_user_id: str


class SocialGraphResponse(BaseModel):
    following: list[str] = []
    followers: list[str] = []
    mutual: list[str] = []
    communities: list[str] = []


@router.get("/social/{user_id}", response_model=SocialGraphResponse)
async def get_social_graph(user_id: str) -> SocialGraphResponse:
    """获取用户社交图谱。骨架实现。"""
    # TODO: Phase 3 接入社交画像
    return SocialGraphResponse()


@router.post("/social/follow")
async def follow_user(req: FollowRequest) -> dict[str, Any]:
    """关注用户。骨架实现。"""
    # TODO: Phase 3 接入社交关系存储
    return {"success": True}
