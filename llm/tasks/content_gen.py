"""LLM 内容模拟生成 — 冷启动辅助"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.tasks.content_gen")

_CONTENT_GEN_PROMPT = """你是一个内容推荐模拟器。根据以下内容特征，生成可能的用户交互数据（模拟5个虚拟用户的行为）:

标题: {title}
标签: {tags}
作者: {author}

请生成 JSON 格式:
{{
  "simulated_interactions": [
    {{"user_type": "...", "click_probability": 0.8, "expected_dwell_sec": 30, "like_probability": 0.3}}
  ]
}}"""


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
        prompt = _CONTENT_GEN_PROMPT.format(
            title=title, tags=", ".join(tags), author=author
        )
        response = await self._llm.generate(prompt)

        try:
            import json
            # 尝试解析 JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception:
            pass

        return {"simulated_interactions": []}
