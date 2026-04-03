"""RecContext 工厂 + 上下文工具函数"""

from __future__ import annotations

from typing import Any

from protocols.schemas.context import Item, RecContext, StageMetrics
from utils.hash import generate_request_id


def create_context(
    user_id: str,
    scene: str = "home_feed",
    request_id: str | None = None,
    page: int = 0,
    page_size: int = 20,
    query: str | None = None,
    context_features: dict[str, Any] | None = None,
) -> RecContext:
    """创建推荐上下文。"""
    return RecContext(
        request_id=request_id or generate_request_id(),
        user_id=user_id,
        scene=scene,
        page=page,
        page_size=page_size,
        query=query,
        context_features=context_features or {},
    )


def add_stage_metrics(
    ctx: RecContext,
    stage_name: str,
    latency_ms: float,
    input_count: int,
    output_count: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """向上下文追加阶段指标。"""
    ctx.stage_metrics.append(StageMetrics(
        stage_name=stage_name,
        latency_ms=latency_ms,
        input_count=input_count,
        output_count=output_count,
        extra=extra or {},
    ))


def get_items_by_source(ctx: RecContext, source: str) -> list[Item]:
    """按来源通道筛选候选物品。"""
    return [item for item in ctx.candidates if item.source == source]


def dedup_items(ctx: RecContext) -> RecContext:
    """按 item_id 去重，保留分数最高的。"""
    seen: dict[str, Item] = {}
    for item in ctx.candidates:
        if item.id not in seen or item.score > seen[item.id].score:
            seen[item.id] = item
    ctx.candidates = list(seen.values())
    return ctx


def sort_by_score(ctx: RecContext) -> RecContext:
    """按分数降序排列候选物品。"""
    ctx.candidates.sort(key=lambda x: x.score, reverse=True)
    return ctx


def truncate_candidates(ctx: RecContext, max_count: int) -> RecContext:
    """截断候选集到指定数量。"""
    ctx.candidates = ctx.candidates[:max_count]
    return ctx
