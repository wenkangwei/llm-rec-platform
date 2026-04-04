"""搜索重排摘要 — LLM 生成个性化搜索摘要"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.rerank_summary")


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
        prompt = get_prompt_manager().render(
            "rerank_summary",
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
