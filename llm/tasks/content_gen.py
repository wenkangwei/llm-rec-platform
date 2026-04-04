"""LLM 内容模拟生成 — 冷启动辅助"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from llm.prompt.manager import get_prompt_manager
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.content_gen")


class ContentGenerator:
    """LLM 内容模拟生成器。

    利用 LLM 基于内容特征生成模拟交互数据，
    辅助冷启动 item 的初始排序分数评估。
    """

    def __init__(self, llm: LLMBackend):
        self._llm = llm

    async def generate_simulated_interactions(
        self, title: str, tags: list[str], author: str = ""
    ) -> dict[str, Any]:
        """为新内容生成模拟交互数据。"""
        prompt = get_prompt_manager().render(
            "content_gen", title=title, tags=", ".join(tags), author=author
        )
        response = await self._llm.generate(prompt)

        try:
            import json
            # 尝试解析 JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.debug(f"JSON 解析失败", error=str(e))

        return {"simulated_interactions": []}
