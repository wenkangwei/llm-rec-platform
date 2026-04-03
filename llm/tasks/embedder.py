"""LLM Embedding 生成任务"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.embedder")


class Embedder:
    """LLM Embedding 生成器。

    利用 LLM 理解内容语义，生成高质量 item embedding。
    """

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    async def embed_text(self, text: str) -> list[float]:
        """生成单个文本的 embedding。"""
        embeddings = await self._llm.embed(text)
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """批量生成 embedding。"""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self._llm.embed(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_item(self, item_id: str, title: str, tags: list[str], description: str = "") -> list[float]:
        """生成物品的语义 embedding。"""
        text = f"{title} {' '.join(tags)} {description}".strip()
        return await self.embed_text(text)
