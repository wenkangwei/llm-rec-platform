"""LLMBackend — LLM 后端抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class LLMBackend(ABC):
    """LLM 后端统一接口。"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """同步生成。"""

    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式生成。"""

    @abstractmethod
    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """生成 embedding。"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查。"""

    @abstractmethod
    async def warmup(self) -> None:
        """预热。"""

    async def shutdown(self) -> None:
        """关闭。"""
