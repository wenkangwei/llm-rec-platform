"""协议转换器 — HTTP Request/Response ↔ RecContext 双向转换

职责分离:
- request.py:  仅定义 HTTP 入参 Pydantic Schema
- response.py: 仅定义 HTTP 出参 Pydantic Schema
- context.py:  仅定义内部 RecContext dataclass
- converters/: 负责双向转换，HTTP 层与 Pipeline 层通过此模块解耦
"""

from __future__ import annotations

from protocols.schemas.context import Item, RecContext
from protocols.schemas.request import (
    CommunityFeedRequest,
    FollowFeedRequest,
    RecRequest,
    SearchRequest,
)
from protocols.schemas.response import RecItem, RecResponse, SearchResponse


# ===== HTTP Request → RecContext =====

def request_to_context(req: RecRequest, request_id: str) -> RecContext:
    """将 HTTP RecRequest 转为内部 RecContext。

    Route 层调用此函数，Pipeline 层不感知 HTTP 协议。
    """
    return RecContext(
        request_id=request_id,
        user_id=req.user_id,
        scene=req.scene,
        page=req.page,
        page_size=req.num,
        context_features=req.context or {},
    )


def search_to_context(req: SearchRequest, request_id: str) -> RecContext:
    """将 HTTP SearchRequest 转为内部 RecContext。"""
    return RecContext(
        request_id=request_id,
        user_id=req.user_id,
        scene="search_feed",
        query=req.query,
        page=req.page,
        page_size=req.num,
        context_features=req.context or {},
    )


def follow_to_context(req: FollowFeedRequest, request_id: str) -> RecContext:
    """将 HTTP FollowFeedRequest 转为内部 RecContext。"""
    return RecContext(
        request_id=request_id,
        user_id=req.user_id,
        scene="follow_feed",
        page=req.page,
        page_size=req.num,
    )


def community_to_context(req: CommunityFeedRequest, request_id: str) -> RecContext:
    """将 HTTP CommunityFeedRequest 转为内部 RecContext。"""
    ctx = RecContext(
        request_id=request_id,
        user_id=req.user_id,
        scene="community_feed",
        page=req.page,
        page_size=req.num,
    )
    if req.community_id:
        ctx.extras["community_id"] = req.community_id
    return ctx


# ===== RecContext → HTTP Response =====

def context_to_response(ctx: RecContext) -> RecResponse:
    """将内部 RecContext 转为 HTTP RecResponse。

    Pipeline 层产出 RecContext，Route 层调用此函数返回给用户。
    """
    visible = ctx.candidates[: ctx.page_size]
    items = [
        RecItem(
            item_id=item.id,
            score=round(item.score, 4),
            source=item.source,
            summary=item.metadata.get("summary"),
            extra={k: v for k, v in item.metadata.items() if k != "summary"} or None,
        )
        for item in visible
    ]
    return RecResponse(
        request_id=ctx.request_id,
        items=items,
        trace_id=ctx.extras.get("trace_id"),
        total=len(ctx.candidates),
        page=ctx.page,
        has_more=len(ctx.candidates) > (ctx.page + 1) * ctx.page_size,
    )


def context_to_search_response(ctx: RecContext) -> SearchResponse:
    """将内部 RecContext 转为 HTTP SearchResponse。"""
    visible = ctx.candidates[: ctx.page_size]
    items = [
        RecItem(
            item_id=item.id,
            score=round(item.score, 4),
            source=item.source,
            summary=item.metadata.get("summary"),
            extra={k: v for k, v in item.metadata.items() if k != "summary"} or None,
        )
        for item in visible
    ]
    return SearchResponse(
        request_id=ctx.request_id,
        query=ctx.query or "",
        items=items,
        trace_id=ctx.extras.get("trace_id"),
        total=len(ctx.candidates),
    )
