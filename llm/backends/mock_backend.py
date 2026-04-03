"""Mock LLM 后端 — 开发/测试用"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.backends.mock")


class MockBackend(LLMBackend):
    """Mock 后端，用于开发和测试。"""

    async def generate(self, prompt: str, **kwargs) -> str:
        return f"[Mock Response] 收到请求: {prompt[:100]}..."

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        response = f"[Mock Stream] {prompt[:50]}..."
        for char in response:
            yield char

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        texts = [text] if isinstance(text, str) else text
        return [[0.1] * 128 for _ in texts]

    async def health_check(self) -> bool:
        return True

    async def warmup(self) -> None:
        logger.info("Mock 后端初始化完成")
