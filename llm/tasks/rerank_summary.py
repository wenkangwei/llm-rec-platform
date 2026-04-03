"""搜索重排摘要 — LLM 生成个性化搜索摘要"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.rerank_summary")

_SUMMARY_PROMPT = """用户搜索了 "{query}"，用户兴趣是 {interests}。
以下是一个搜索结果的内容摘要:
{content}

请基于用户兴趣，生成一个简洁的个性化摘要（不超过50字），突出与用户兴趣相关的内容点:
"""


class RerankSummary:
    """搜索重排摘要生成器。

    基于用户兴趣重新组织搜索结果的展示文本，提升 CTR。
    """

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    async def generate_summary(
        self, query: str, content: str, user_interests: list[str]
    ) -> str:
        """生成个性化搜索摘要。"""
        prompt = _SUMMARY_PROMPT.format(
            query=query,
            interests="、".join(user_interests[:5]),
            content=content[:500],
        )
        return await self._llm.generate(prompt, max_tokens=100, temperature=0.3)

    async def batch_summarize(
        self, query: str, items: list[dict[str, Any]], user_interests: list[str]
    ) -> list[str]:
        """批量生成摘要。"""
        summaries = []
        for item in items:
            content = item.get("content", "")
            summary = await self.generate_summary(query, content, user_interests)
            summaries.append(summary)
        return summaries
