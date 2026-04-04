"""搜索推荐路由 — HTTP Request → RecContext → Pipeline → SearchResponse"""

from __future__ import annotations

from fastapi import APIRouter, Request

from protocols.schemas.converters import context_to_search_response, search_to_context
from protocols.schemas.request import SearchRequest
from protocols.schemas.response import SearchResponse
from utils.logger import get_struct_logger

logger = get_struct_logger("server.routes.search")

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    """搜索推荐接口。

    流程: HTTP SearchRequest → search_to_context() → PipelineExecutor → LLM 摘要 → SearchResponse
    """
    request_id = getattr(request.state, "request_id", "")

    # HTTP → RecContext
    ctx = search_to_context(req, request_id)

    # Pipeline 执行
    executor = getattr(request.app.state, "pipeline_executor", None)
    if executor:
        ctx = await executor.execute(ctx)

    # LLM 搜索摘要生成
    llm_backend = getattr(request.app.state, "llm_backend", None)
    if llm_backend and ctx.candidates:
        ctx = await _generate_search_summary(ctx, req.query, llm_backend)

    # RecContext → HTTP Response（含 LLM 摘要）
    resp = context_to_search_response(ctx)
    if ctx.extras.get("search_summary"):
        resp.summary = ctx.extras["search_summary"]
    return resp


async def _generate_search_summary(ctx, query: str, llm_backend) -> object:
    """使用 LLM 对搜索结果生成摘要。

    摘要用于搜索结果页顶部，帮助用户快速了解搜索结果概况。
    """
    # 限制传入的候选数量，避免 token 过长
    top_items = ctx.candidates[:10]
    if not top_items:
        return ctx

    item_descriptions = []
    for item in top_items[:5]:
        title = item.metadata.get("title", "") if item.metadata else ""
        if title:
            item_descriptions.append(f"- {title} (score: {item.score:.2f})")

    if not item_descriptions:
        return ctx

    prompt = (
        f"用户搜索了「{query}」，以下是相关搜索结果：\n"
        + "\n".join(item_descriptions)
        + "\n\n请用 1-2 句话简要概括这些搜索结果的内容特点。"
    )

    try:
        summary = await llm_backend.generate(prompt, max_tokens=128, temperature=0.3)
        if summary:
            ctx.extras["search_summary"] = summary.strip()
            logger.info(f"搜索摘要生成成功", query=query, summary_len=len(summary))
    except Exception as e:
        logger.warning(f"搜索摘要生成失败", query=query, error=str(e))

    return ctx
