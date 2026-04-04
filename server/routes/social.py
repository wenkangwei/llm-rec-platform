"""社交相关路由 — 社交图谱查询与关注操作"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from utils.logger import get_struct_logger

logger = get_struct_logger("server.routes.social")

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
async def get_social_graph(user_id: str, request: Request) -> SocialGraphResponse:
    """获取用户社交图谱。

    从社交画像存储中读取用户的关注/粉丝/互关/社区信息。
    """
    # 尝试从特征平台获取社交画像
    feature_platform = getattr(request.app.state, "feature_platform", None)
    if feature_platform:
        try:
            profile = feature_platform.get_profile("social", user_id)
            if profile:
                return SocialGraphResponse(
                    following=profile.get("following", []),
                    followers=profile.get("followers", []),
                    mutual=profile.get("mutual", []),
                    communities=profile.get("communities", []),
                )
        except Exception as e:
            logger.warning(f"社交画像获取失败: {user_id}", error=str(e))

    # 无画像时从 Redis 获取
    redis_store = getattr(request.app.state, "redis_store", None)
    if redis_store:
        try:
            social_data = await redis_store.get(f"social:{user_id}")
            if social_data:
                return SocialGraphResponse(**social_data)
        except Exception as e:
            logger.warning(f"Redis 社交数据获取失败: {user_id}", error=str(e))

    return SocialGraphResponse()


@router.post("/social/follow")
async def follow_user(req: FollowRequest, request: Request) -> dict[str, Any]:
    """关注用户。

    写入社交关系，更新双方的关注/粉丝列表。
    """
    redis_store = getattr(request.app.state, "redis_store", None)
    if not redis_store:
        logger.warning("Redis 存储不可用，关注操作未持久化")
        return {"success": True, "persisted": False}

    try:
        # 更新关注者的关注列表
        following_key = f"social:{req.user_id}"
        following_data = await redis_store.get(following_key) or {}
        following_list = following_data.get("following", [])
        if req.target_user_id not in following_list:
            following_list.append(req.target_user_id)
            following_data["following"] = following_list
            await redis_store.set(following_key, following_data)

        # 更新被关注者的粉丝列表
        follower_key = f"social:{req.target_user_id}"
        follower_data = await redis_store.get(follower_key) or {}
        followers_list = follower_data.get("followers", [])
        if req.user_id not in followers_list:
            followers_list.append(req.user_id)
            follower_data["followers"] = followers_list
            await redis_store.set(follower_key, follower_data)

        logger.info(f"关注成功", user=req.user_id, target=req.target_user_id)
        return {"success": True, "persisted": True}
    except Exception as e:
        logger.error(f"关注操作失败", error=str(e))
        return {"success": False, "error": str(e)}
