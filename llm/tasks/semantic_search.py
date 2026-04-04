"""语义搜索 — 基于 LLM 的语义理解搜索"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.semantic_search")


class SemanticSearch:
    """语义搜索引擎。

    1. 用 LLM 扩展搜索 query
    2. 结合向量检索获取候选
    3. 用 LLM 语义重排
    """

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    async def expand_query(self, query: str) -> list[str]:
        """扩展搜索 query。"""
        prompt = get_prompt_manager().render("query_expand", query=query)
        response = await self._llm.generate(prompt, max_tokens=200, temperature=0.5)
        # 解析每行
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        return [query] + lines[:5]

    async def semantic_search(
        self, query: str, faiss_store=None, top_k: int = 50
    ) -> list[dict[str, Any]]:
        """语义搜索完整流程。"""
        # 1. 扩展 query
        expanded = await self.expand_query(query)
        logger.info(f"Query 扩展", original=query, expanded=expanded)

        # 2. 向量检索（需要 faiss_store 注入）
        if faiss_store is None:
            return []

        # 3. 生成 query embedding 并搜索
        query_emb = await self._llm.embed(query)
        if query_emb and query_emb[0]:
            import numpy as np
            scores, ids = faiss_store.search(
                np.array(query_emb[0], dtype=np.float32).reshape(1, -1), top_k
            )
            results = []
            for score_list, id_list in zip(scores, ids):
                for score, item_id in zip(score_list, id_list):
                    if item_id:
                        results.append({"item_id": item_id, "score": float(score)})
            return results

        return []
